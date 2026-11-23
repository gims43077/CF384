"""All provider results are synthetic fixtures. No paid/live internet search is called."""
import asyncio
import io
import json
import secrets
import sys
import time
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cf384_api.config import Settings
from cf384_api.app import create_app
from cf384_api.engine import Detector
from cf384_api import web_search as module
from cf384_api.web_search import WebSearch,ProviderError,normalize,safe_url,search_image

def image(color=30):
    stream=io.BytesIO();Image.new('RGB',(180,120),(color,100,170)).save(stream,format='PNG');return stream.getvalue()

def result(matches=True):
    return {'search_metadata':{'status':'Success'},'exact_matches':[{'image':'https://images.example.org/copy.jpg','title':'Fixture usage','link':'https://example.org/article','thumbnail':'https://images.example.org/thumb.jpg'},{'link':'javascript:alert(1)'}] if matches else []}

def settings(**kw):
    return Settings(api_key=secrets.token_urlsafe(32),web_search_enabled=kw.pop('web_search_enabled',True),serpapi_api_key=kw.pop('serpapi_api_key','fixture-only-provider-key'),**kw)

def run(coro):return asyncio.run(coro)

@pytest.mark.parametrize('enabled,key,requested,expected',[(True,'fixture',False,'not_requested'),(False,'fixture',True,'disabled'),(True,'',True,'not_configured')])
def test_no_network_without_all_three_optins(enabled,key,requested,expected):
    def forbidden(*a):raise AssertionError('Unexpected provider call')
    service=WebSearch(settings(web_search_enabled=enabled,serpapi_api_key=key),transport=forbidden)
    assert run(service.search(image(),requested))['status']==expected
    assert service.calls==0

def test_sanitized_matches_cache_and_session_budget():
    calls=[]
    def provider(raw,key,timeout):calls.append(raw);return result()
    async def scenario():
        service=WebSearch(settings(web_search_max_calls=1),transport=provider)
        a=await service.search(image(),True);b=await service.search(image(),True);c=await service.search(image(31),True)
        assert a['status']=='matches_found' and len(a['matches'][0]['backlinks'])==1
        assert a['matches'][0]['backlinks'][0]['page_url']=='https://example.org/article'
        assert b['cached'] and b['searched_at']==a['searched_at']
        assert c['status']=='rate_limited' and c['error_code']=='session_call_limit'
        assert service.calls==1 and len(calls)==1 and calls[0].startswith(b'\xff\xd8')
    run(scenario())

def test_empty_index_result_is_not_error_and_not_claim_of_unused():
    service=WebSearch(settings(),transport=lambda *a:result(False))
    r=run(service.search(image(),True));assert r['status']=='no_matches' and r['matches']==[]
    assert 'does not mean unused' in r['notice']

@pytest.mark.parametrize('error',[ProviderError('provider_auth_failed'),TimeoutError('fixture-only-provider-key in unsafe error')])
def test_error_is_explicit_redacted_and_not_cached(error):
    def fail(*a):raise error
    async def scenario():
        s=WebSearch(settings(),transport=fail);a=await s.search(image(),True);b=await s.search(image(),True)
        assert a['status']=='error' and a['searched_at'] is None and not a['cached']
        assert 'fixture-only-provider-key' not in json.dumps(a)
        assert b['status']=='rate_limited' and s.calls==1
    run(scenario())

def test_per_minute_limit():
    async def scenario():
        s=WebSearch(settings(),transport=lambda *a:result(False))
        for n in range(5):assert (await s.search(image(40+n),True))['status']=='no_matches'
        assert (await s.search(image(50),True))['status']=='rate_limited';assert s.calls==5
    run(scenario())

def test_concurrent_duplicate_requests_share_one_provider_call():
    calls=[]
    def provider(*a):calls.append(True);time.sleep(.1);return result()
    async def scenario():
        s=WebSearch(settings(),transport=provider)
        a,b=await asyncio.gather(s.search(image(),True),s.search(image(),True))
        assert a['status']==b['status']=='matches_found' and len(calls)==1
        assert sum(x['cached'] for x in (a,b))==1
    run(scenario())

def test_saturated_provider_queue_returns_bounded_search_results():
    def provider(*a):time.sleep(.1);return result(False)
    async def scenario():
        s=WebSearch(settings(),transport=provider)
        results=await asyncio.gather(*(s.search(image(n+60),True) for n in range(8)))
        assert sum(r['status']=='no_matches' for r in results)<=4
        assert sum(r['status']=='rate_limited' for r in results)>=4
        assert s.calls<=4
    run(scenario())

def test_expired_cache_calls_provider_again(monkeypatch):
    clock=[1000.0];monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    async def scenario():
        s=WebSearch(settings(web_search_cache_ttl=1),transport=lambda *a:result(False))
        await s.search(image(),True);clock[0]+=2
        b=await s.search(image(),True);assert not b['cached'] and s.calls==2
    run(scenario())

def test_provider_request_wire_protocol_without_network(monkeypatch):
    from urllib.parse import urlsplit,parse_qs
    seen=[]
    class Response:
        def __init__(self,obj):self.obj=obj
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,limit):return json.dumps(self.obj).encode()
    class Opener:
        def open(self,req,timeout):
            p=urlsplit(req.full_url);seen.append(p.path);assert p.scheme=='https' and p.hostname=='serpapi.com'
            if p.path=='/account.json':
                assert parse_qs(p.query)['api_key']==['fixture-key']
                return Response(free_account())
            if p.path=='/image':
                assert b'name="image"' in req.data and b'fixture-image-bytes' in req.data
                assert b'name="api_key"' in req.data
                return Response({'image_id':'fixture-image-id'})
            assert p.path=='/search'
            q=parse_qs(p.query);assert q['type']==['exact_matches'] and q['engine']==['google_lens'] and q['image_id']==['fixture-image-id']
            return Response(result())
    monkeypatch.setattr(module.urllib.request,'build_opener',lambda *a:Opener())
    assert module.upload_serpapi(b'fixture-image-bytes','fixture-key',20)['search_metadata']['status']=='Success'
    assert seen==['/account.json','/image','/search']


def free_account():
    return dict(plan_id='free',plan_name='Free Plan',plan_monthly_price=0,plan_searches_left=200,extra_credits=0,this_hour_searches=0,account_rate_limit_per_hour=50)


@pytest.mark.parametrize('change,code',[
    ({'plan_id':'developer','plan_name':'Developer','plan_monthly_price':25},'free_plan_required'),
    ({'plan_searches_left':0},'free_quota_exhausted'),
    ({'extra_credits':100},'free_plan_required'),
    ({'plan_monthly_price':None},'free_account_check_failed'),
    ({'this_hour_searches':50},'free_hourly_quota_exhausted')])
def test_nonfree_or_exhausted_accounts_never_upload_or_search(monkeypatch,change,code):
    account=free_account();account.update(change);seen=[]
    def call(url,*a,**kw):
        seen.append(url);assert '/account.json?' in url;return account
    monkeypatch.setattr(module,'request_json',call)
    with pytest.raises(ProviderError) as err:module.upload_serpapi(image(),'fixture-key',20)
    assert err.value.code==code and len(seen)==1


def test_similar_only_results_are_not_reported_as_reuse():
    with pytest.raises(ProviderError) as err:normalize({'search_metadata':{'status':'Success'},'visual_matches':[{'link':'https://example.org'}]})
    assert err.value.code=='unexpected_search_type'


def test_noise_image_fits_upload_limit():
    import numpy as np
    im=Image.fromarray(np.random.default_rng(12).integers(0,256,(1800,1800,3),dtype=np.uint8));stream=io.BytesIO();im.save(stream,format='PNG')
    assert len(search_image(stream.getvalue()))<=480000


def test_free_plan_block_keeps_explicit_status():
    def reject(*a):raise ProviderError('free_plan_required')
    r=run(WebSearch(settings(),transport=reject).search(image(),True));assert r['status']=='blocked' and r['error_code']=='free_plan_required'

@pytest.mark.parametrize('obj',[{}, {'results':{}}, {'results':{'matches':'bad'}}])
def test_malformed_provider_response(obj):
    with pytest.raises(ProviderError):normalize(obj)

def test_upload_preserves_full_aspect_ratio_and_removes_metadata():
    im=Image.new('RGB',(3200,1800),'red');exif=Image.Exif();exif[270]='private fixture metadata';stream=io.BytesIO();im.save(stream,format='JPEG',exif=exif)
    raw=search_image(stream.getvalue())
    with Image.open(io.BytesIO(raw)) as out:assert out.size==(1600,900) and len(out.getexif())==0
    assert safe_url('https://user:password@example.org') is None
    assert safe_url('javascript:alert(1)') is None
    assert 'fixture-only-provider-key' not in repr(settings())

def test_api_combines_real_cf_scores_with_mock_web_usage():
    if not (ROOT/'models/cf384.safetensors').exists():pytest.skip('Download official backbone first')
    cfg=settings(allowed_hosts=('testserver',),web_search_max_calls=2)
    with TestClient(create_app(cfg,Detector(cfg))) as client:
        calls=[]
        def provider(*args):calls.append(True);return result()
        client.app.state.web_search.transport=provider
        headers={'X-API-Key':cfg.api_key};files={'file':('fixture.png',image(),'image/png')}
        assert client.post('/v1/predict?web_search=true',files=files).status_code==401
        bad=client.post('/v1/predict?web_search=true',headers=headers,files={'file':('bad',b'bad','image/png')})
        assert bad.status_code==415 and not calls
        default=client.post('/v1/predict',headers=headers,files=files).json();assert default['web_usage']['status']=='not_requested' and not calls
        a=client.post('/v1/predict?web_search=true',headers=headers,files=files).json()
        b=client.post('/v1/predict?web_search=true',headers=headers,files=files).json()
        assert a['scores']==default['scores'] and a['selected_model']=='lowres'
        assert a['web_usage']['status']=='matches_found' and b['web_usage']['cached'] and len(calls)==1
        def fail(*args):raise ProviderError('provider_unavailable')
        client.app.state.web_search.transport=fail
        c=client.post('/v1/predict?web_search=true',headers=headers,files={'file':('fixture.png',image(60),'image/png')})
        assert c.status_code==200 and c.json()['web_usage']['status']=='error'
        assert c.json()['result']==c.json()['scores']['lowres']
        status=client.get('/v1/web-search/status',headers=headers).json()
        assert status['provider_calls_this_session']==2 and cfg.serpapi_api_key not in json.dumps(status)

def test_provider_key_file_permissions(tmp_path):
    from configure_web_search import store_key
    p=tmp_path/'key.txt';store_key('fixture-only-key',p)
    assert p.read_text().strip()=='fixture-only-key'
    if sys.platform!='win32':assert p.stat().st_mode & 0o777==0o600

def test_api_paid_account_is_blocked_before_upload(monkeypatch):
    if not (ROOT/'models/cf384.safetensors').exists():pytest.skip('Download official backbone first')
    seen=[]
    def account_only(url,*a,**kw):
        seen.append(url);assert '/account.json?' in url
        return dict(plan_id='developer',plan_name='Developer',plan_monthly_price=25,plan_searches_left=100,extra_credits=0)
    monkeypatch.setattr(module,'request_json',account_only)
    cfg=settings(allowed_hosts=('testserver',))
    with TestClient(create_app(cfg,Detector(cfg))) as client:
        r=client.post('/v1/predict?web_search=true',headers={'X-API-Key':cfg.api_key},files={'file':('fixture.png',image(),'image/png')})
        assert r.status_code==200
        out=r.json();assert out['web_usage']['status']=='blocked' and out['web_usage']['error_code']=='free_plan_required'
        assert out['result']==out['scores']['lowres'] and len(seen)==1
