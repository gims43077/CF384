"""Free-plan-only SerpApi Google Lens exact matches; no paid-provider fallback."""
import asyncio,copy,hashlib,io,json,math,time,urllib.error,urllib.request,uuid
from collections import OrderedDict,deque
from datetime import datetime,timezone
from urllib.parse import urlencode,urlsplit
from PIL import Image,ImageOps

PROVIDER='serpapi_google_lens'
NOTICE=('Provider exact-match candidates require confirmation. Index coverage is incomplete; '
        'no match does not mean unused. Results do not establish ownership, publication date, '
        'copyright infringement, or AI generation. Paid accounts and paid-provider fallback are blocked.')

class ProviderError(Exception):
    def __init__(self,code):self.code=code;super().__init__(code)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def search_image(raw):
    """Whole image, no EXIF/GPS, aspect preserved, below the 500KB upload limit."""
    with Image.open(io.BytesIO(raw)) as source:im=ImageOps.exif_transpose(source).convert('RGB')
    im.thumbnail((1600,1600),Image.Resampling.LANCZOS)
    for _ in range(8):
        for quality in (90,80,65,50):
            stream=io.BytesIO();im.save(stream,format='JPEG',quality=quality,subsampling=2)
            data=stream.getvalue()
            if len(data)<=480000:return data
        im=im.resize((max(1,int(im.width*.75)),max(1,int(im.height*.75))),Image.Resampling.LANCZOS)
    raise ProviderError('upload_image_too_large')

def request_json(url,timeout,data=None,content_type=None):
    headers={'User-Agent':'CF384-Local-API/1.4'}
    if content_type:headers['Content-Type']=content_type
    req=urllib.request.Request(url,data=data,headers=headers,method='POST' if data is not None else 'GET')
    try:
        # Keys appear in documented parameters: never log URLs/errors or redirect.
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=timeout) as response:raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ProviderError('provider_response_too_large')
        obj=json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ProviderError('provider_rate_limited' if exc.code==429 else 'provider_auth_failed' if exc.code in (401,403) else 'provider_http_error') from None
    except ProviderError:raise
    except (urllib.error.URLError,OSError,TimeoutError):raise ProviderError('provider_unavailable') from None
    except (ValueError,UnicodeError):raise ProviderError('invalid_provider_response') from None
    if not isinstance(obj,dict):raise ProviderError('invalid_provider_response')
    if obj.get('error'):raise ProviderError('provider_rejected_request')
    return obj

def validate_free_account(account):
    """Fail closed before upload/search. Account API is documented as free."""
    if str(account.get('plan_id') or '').lower()!='free' and str(account.get('plan_name') or '').lower() not in ('free','free plan'):
        raise ProviderError('free_plan_required')
    values=[account.get(k) for k in ('plan_monthly_price','plan_searches_left','extra_credits')]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ProviderError('free_account_check_failed')
    price,left,extra=values
    if price!=0 or extra!=0:raise ProviderError('free_plan_required')
    if left<=0:raise ProviderError('free_quota_exhausted')
    used=account.get('this_hour_searches');limit=account.get('account_rate_limit_per_hour')
    if isinstance(used,(int,float)) and isinstance(limit,(int,float)) and used>=limit:raise ProviderError('free_hourly_quota_exhausted')

def upload_serpapi(raw,api_key,timeout):
    account=request_json('https://serpapi.com/account.json?'+urlencode({'api_key':api_key}),timeout)
    validate_free_account(account)
    boundary='cf384-'+uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="api_key"\r\n\r\n{api_key}\r\n'
          f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="image.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode()+raw+f'\r\n--{boundary}--\r\n'.encode()
    obj=request_json('https://serpapi.com/image',timeout,data=body,content_type='multipart/form-data; boundary='+boundary)
    image_id=obj.get('image_id')
    if not isinstance(image_id,str) or not image_id or len(image_id)>2048:raise ProviderError('invalid_upload_response')
    params=dict(engine='google_lens',type='exact_matches',image_id=image_id,api_key=api_key,output='json')
    return request_json('https://serpapi.com/search?'+urlencode(params),timeout)

def safe_url(value):
    if not isinstance(value,str) or len(value)>8192:return None
    try:
        p=urlsplit(value)
        return value if p.scheme.lower() in ('http','https') and p.hostname and not p.username and not p.password else None
    except ValueError:return None

def normalize(obj):
    meta=obj.get('search_metadata',{})
    if obj.get('error') or not isinstance(meta,dict) or meta.get('status')!='Success':raise ProviderError('invalid_provider_response')
    if 'exact_matches' not in obj:
        if obj.get('visual_matches'):raise ProviderError('unexpected_search_type')
        raise ProviderError('missing_exact_match_results')
    items=obj['exact_matches']
    if not isinstance(items,list):raise ProviderError('invalid_provider_response')
    matches=[]
    for row in items[:10]:
        if not isinstance(row,dict):raise ProviderError('invalid_provider_response')
        page=safe_url(row.get('link'))
        if not page:continue
        image=safe_url(row.get('image'));thumb=safe_url(row.get('thumbnail'));title=row.get('title')
        matches.append(dict(image_url=image,thumbnail_url=thumb,domain=urlsplit(page).hostname,title=title[:1000] if isinstance(title,str) else None,provider_score=None,match_kind='provider_exact_match',backlinks=[dict(page_url=page,image_url=image,crawl_date=None)]))
    if items and not matches:raise ProviderError('invalid_provider_response')
    return matches,len(items)

class WebSearch:
    def __init__(self,settings,transport=None):
        self.settings=settings;self.transport=transport or upload_serpapi
        self.cache=OrderedDict();self.lock=None;self.calls=0;self.recent=deque();self.hourly=deque();self.cooldown_until=0;self.pending=0

    def status(self):
        return dict(provider=PROVIDER,enabled=self.settings.web_search_enabled,configured=bool(self.settings.serpapi_api_key),ready=self.settings.web_search_enabled and bool(self.settings.serpapi_api_key),quota_policy='free_plan_only',paid_fallback=False,provider_calls_this_session=self.calls,max_provider_calls=self.settings.web_search_max_calls,requests_per_minute=5,requests_per_hour=40,cache_ttl_seconds=self.settings.web_search_cache_ttl,upload_transform='Full image, EXIF metadata removed, max1600px aspect-preserving JPEG, <=480KB',notice=NOTICE)

    def result(self,status,**extra):
        return dict(status=status,provider=PROVIDER,searched_at=None,cached=False,matches=[],returned_matches=0,provider_matches_in_page=None,notice=NOTICE,**extra)

    async def search(self,raw,requested):
        if not requested:return self.result('not_requested')
        if not self.settings.web_search_enabled:return self.result('disabled')
        if not self.settings.serpapi_api_key:return self.result('not_configured')
        if self.lock is None:self.lock=asyncio.Lock()
        if self.pending>=4:return self.result('rate_limited',error_code='web_search_busy')
        self.pending+=1
        try:
            try:await asyncio.wait_for(self.lock.acquire(),timeout=1)
            except asyncio.TimeoutError:return self.result('rate_limited',error_code='web_search_busy')
            try:return await self._search_locked(raw)
            finally:self.lock.release()
        finally:self.pending-=1

    async def _search_locked(self,raw):
        digest=hashlib.sha256(raw).hexdigest();now=time.monotonic()
        if digest in self.cache:
            expiry,result=self.cache.pop(digest)
            if expiry>now:
                self.cache[digest]=(expiry,result);out=copy.deepcopy(result);out['cached']=True;return out
        while self.recent and self.recent[0]<=now-60:self.recent.popleft()
        while self.hourly and self.hourly[0]<=now-3600:self.hourly.popleft()
        if self.calls>=self.settings.web_search_max_calls:return self.result('rate_limited',error_code='session_call_limit')
        if len(self.recent)>=5 or len(self.hourly)>=40 or now<self.cooldown_until:return self.result('rate_limited',error_code='provider_call_cooldown')
        self.calls+=1;self.recent.append(now);self.hourly.append(now)
        try:
            upload=await asyncio.to_thread(search_image,raw)
            obj=await asyncio.to_thread(self.transport,upload,self.settings.serpapi_api_key,self.settings.web_search_timeout)
            matches,reported=normalize(obj)
        except ProviderError as exc:
            self.cooldown_until=time.monotonic()+60
            return self.result('blocked' if exc.code.startswith('free_') else 'error',error_code=exc.code)
        except Exception:
            self.cooldown_until=time.monotonic()+60
            return self.result('error',error_code='provider_unavailable')
        out=self.result('matches_found' if matches else 'no_matches')
        out.update(searched_at=datetime.now(timezone.utc).isoformat(),matches=matches,returned_matches=len(matches),provider_matches_in_page=reported)
        self.cache[digest]=(time.monotonic()+self.settings.web_search_cache_ttl,copy.deepcopy(out))
        while len(self.cache)>128:self.cache.popitem(last=False)
        return out
