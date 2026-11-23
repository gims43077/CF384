"""Optional TinEye reverse search. No crawling, retries, purchases, or image persistence."""
import asyncio
import copy
import hashlib
import io
import json
import math
import time
import urllib.error
import urllib.request
import uuid
from collections import OrderedDict,deque
from datetime import datetime,timezone
from urllib.parse import urlsplit
from PIL import Image,ImageOps

NOTICE=('Matches cover the provider index only. No match does not mean unused. '
        'Crawl dates are not publication dates or proof of first ownership. '
        'Matching does not determine AI generation or copyright infringement.')

def search_image(raw):
    # Full image, not CF384's central crop; do not transmit EXIF/GPS metadata.
    with Image.open(io.BytesIO(raw)) as source:im=ImageOps.exif_transpose(source).convert('RGB')
    im.thumbnail((1600,1600),Image.Resampling.LANCZOS)
    stream=io.BytesIO();im.save(stream,format='JPEG',quality=90,subsampling=2)
    return stream.getvalue()

class ProviderError(Exception):
    def __init__(self,code):self.code=code;super().__init__(code)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def upload_tineye(raw,api_key,timeout):
    """Wire format verified against TinEye's official pytineye client (v3)."""
    boundary='cf384-'+uuid.uuid4().hex
    fields={'limit':'10','offset':'0','sort':'score','order':'desc'}
    body=b''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k,v in fields.items())
    body+=f'--{boundary}\r\nContent-Disposition: form-data; name="image_upload"; filename="image.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()+raw+f'\r\n--{boundary}--\r\n'.encode()
    req=urllib.request.Request('https://api.tineye.com/rest/search/',data=body,headers={'X-API-Key':api_key,'Content-Type':'multipart/form-data; boundary='+boundary,'User-Agent':'CF384-Local-API/1.3'},method='POST')
    try:
        # Never follow redirects with a provider key or uploaded photo.
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=timeout) as response:
            data=response.read(2*1024*1024+1)
        if len(data)>2*1024*1024:raise ProviderError('provider_response_too_large')
        obj=json.loads(data)
    except urllib.error.HTTPError as exc:
        code='provider_rate_limited' if exc.code==429 else 'provider_auth_failed' if exc.code in (401,403) else 'provider_http_error'
        raise ProviderError(code) from None
    except ProviderError:raise
    except (urllib.error.URLError,TimeoutError,OSError):raise ProviderError('provider_unavailable') from None
    except (ValueError,UnicodeError):raise ProviderError('invalid_provider_response') from None
    if not isinstance(obj,dict) or obj.get('code')!=200:raise ProviderError('provider_rejected_search')
    return obj

def safe_url(value):
    if not isinstance(value,str) or len(value)>8192:return None
    try:
        p=urlsplit(value)
        return value if p.scheme.lower() in ('http','https') and p.hostname and not p.username and not p.password else None
    except ValueError:return None

def normalize(obj):
    results=obj.get('results')
    if not isinstance(results,dict) or not isinstance(results.get('matches'),list):raise ProviderError('invalid_provider_response')
    matches=[]
    for item in results['matches'][:10]:
        if not isinstance(item,dict):raise ProviderError('invalid_provider_response')
        score=item.get('score');score=float(score) if isinstance(score,(int,float)) and not isinstance(score,bool) and math.isfinite(score) and 0<=score<=100 else None
        backlinks=[];seen=set();links=item.get('backlinks') or []
        if not isinstance(links,list):raise ProviderError('invalid_provider_response')
        for link in links[:30]:
            if not isinstance(link,dict):continue
            page=safe_url(link.get('backlink'));image=safe_url(link.get('url'))
            if not page or (page,image) in seen:continue
            seen.add((page,image));date=link.get('crawl_date')
            backlinks.append(dict(page_url=page,image_url=image,crawl_date=str(date)[:100] if date is not None else None))
        image=safe_url(item.get('image_url'))
        if not backlinks and not image:continue
        matches.append(dict(image_url=image,domain=urlsplit(backlinks[0]['page_url'] if backlinks else image).hostname,provider_score=score,backlinks=backlinks))
    return matches,len(results['matches'])

class WebSearch:
    def __init__(self,settings,transport=None):
        self.settings=settings;self.transport=transport or upload_tineye
        self.cache=OrderedDict();self.lock=None;self.calls=0;self.recent=deque();self.cooldown_until=0;self.pending=0

    def status(self):
        return dict(provider='tineye',enabled=self.settings.web_search_enabled,configured=bool(self.settings.tineye_api_key),ready=self.settings.web_search_enabled and bool(self.settings.tineye_api_key),provider_calls_this_session=self.calls,max_provider_calls=self.settings.web_search_max_calls,requests_per_minute=5,cache_ttl_seconds=self.settings.web_search_cache_ttl,upload_transform='EXIF orientation, full image max1600px preserving aspect ratio, JPEG90, metadata removed',notice=NOTICE)

    def result(self,status,**extra):
        return dict(status=status,provider='tineye',searched_at=None,cached=False,matches=[],returned_matches=0,provider_matches_in_page=None,notice=NOTICE,**extra)

    async def search(self,raw,requested):
        if not requested:return self.result('not_requested')
        if not self.settings.web_search_enabled:return self.result('disabled')
        if not self.settings.tineye_api_key:return self.result('not_configured')
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
        digest=hashlib.sha256(raw).hexdigest()
        now=time.monotonic()
        if digest in self.cache:
            expiry,result=self.cache.pop(digest)
            if expiry>now:
                self.cache[digest]=(expiry,result);out=copy.deepcopy(result);out['cached']=True;return out
        while self.recent and self.recent[0]<=now-60:self.recent.popleft()
        if self.calls>=self.settings.web_search_max_calls:return self.result('rate_limited',error_code='session_call_limit')
        if len(self.recent)>=5 or now<self.cooldown_until:return self.result('rate_limited',error_code='provider_call_cooldown')
        # Count attempts even on timeout: a provider might still bill that call.
        self.calls+=1;self.recent.append(now)
        try:
            upload=await asyncio.to_thread(search_image,raw)
            obj=await asyncio.to_thread(self.transport,upload,self.settings.tineye_api_key,self.settings.web_search_timeout)
            matches,reported=normalize(obj)
        except ProviderError as exc:
            self.cooldown_until=time.monotonic()+60
            return self.result('error',error_code=exc.code)
        except Exception:
            # Never return/log provider exception text: it may contain secrets.
            self.cooldown_until=time.monotonic()+60
            return self.result('error',error_code='provider_unavailable')
        out=self.result('matches_found' if matches else 'no_matches')
        out.update(searched_at=datetime.now(timezone.utc).isoformat(),matches=matches,returned_matches=len(matches),provider_matches_in_page=reported)
        if reported and not matches:return self.result('error',error_code='invalid_provider_response')
        self.cache[digest]=(time.monotonic()+self.settings.web_search_cache_ttl,copy.deepcopy(out))
        while len(self.cache)>128:self.cache.popitem(last=False)
        return out
