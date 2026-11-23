import asyncio
from contextlib import asynccontextmanager
import hmac
import logging
import time
import uuid
from typing import Literal,Optional
from fastapi import Depends,FastAPI,File,HTTPException,Request,UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from . import __version__
from .config import ROOT,Settings,read_or_create_key
from .engine import Detector,ImageError,MODEL_ID,NOTICE
from .schemas import Prediction
from .web_search import WebSearch

LOGGER=logging.getLogger('cf384_api')

def error(status,code,message,request_id=None,headers=None):
    return JSONResponse(status_code=status,content={'error':{'code':code,'message':message},'request_id':request_id or str(uuid.uuid4())},headers=headers)

class RequestGate:
    """Reject unwanted origins/keys and oversized bodies before parsing multipart."""
    def __init__(self,app,settings):self.app=app;self.settings=settings
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]));request_id=str(uuid.uuid4());scope.setdefault('state',{})['request_id']=request_id
        origin=headers.get(b'origin',b'').decode('latin1')
        if origin and not self.settings.permits_origin(origin):return await error(403,'origin_not_allowed','This browser origin is not allowed.',request_id)(scope,receive,send)
        if scope['method']!='OPTIONS' and scope['path'].startswith('/v1/'):
            key=headers.get(b'x-api-key',b'')
            if not hmac.compare_digest(key,self.settings.api_key.encode('utf8')):return await error(401,'invalid_api_key','Supply a valid X-API-Key header.',request_id)(scope,receive,send)
        if scope['method'] in ('POST','PUT','PATCH'):
            limit=self.settings.max_image_bytes+512*1024
            try:declared=int(headers.get(b'content-length',b'0'))
            except ValueError:return await error(400,'invalid_content_length','Invalid Content-Length.',request_id)(scope,receive,send)
            if declared>limit:return await error(413,'request_too_large',f'Request body exceeds {limit} bytes.',request_id)(scope,receive,send)
            chunks=[];size=0
            while True:
                message=await receive()
                if message['type']=='http.disconnect':return
                chunk=message.get('body',b'');size+=len(chunk)
                if size>limit:return await error(413,'request_too_large',f'Request body exceeds {limit} bytes.',request_id)(scope,receive,send)
                chunks.append(chunk)
                if not message.get('more_body',False):break
            payload=b''.join(chunks);del chunks;del chunk;del message
            sent=False
            async def replay():
                nonlocal sent
                if not sent:sent=True;return {'type':'http.request','body':payload,'more_body':False}
                return await receive()
            return await self.app(scope,replay,send)
        await self.app(scope,receive,send)

def create_app(settings: Optional[Settings]=None,detector=None):
    settings=settings or Settings(api_key=read_or_create_key())
    @asynccontextmanager
    async def lifespan(app):
        app.state.detector=detector or Detector(settings);app.state.semaphore=asyncio.Semaphore(1);app.state.pending=0
        app.state.web_search=WebSearch(settings)
        yield
        app.state.detector.close()
    app=FastAPI(title='CF384 Local Image Detection API',version=__version__,description='Local still-image inference. Scores are estimates, not image authenticity verification. X-API-Key required for /v1/*.',lifespan=lifespan)
    app.state.settings=settings
    api_key=APIKeyHeader(name='X-API-Key',auto_error=False)
    async def authorized(key=Depends(api_key)):
        if not key or not hmac.compare_digest(key.encode('utf8'),settings.api_key.encode('utf8')):raise HTTPException(401,detail={'code':'invalid_api_key','message':'Supply a valid X-API-Key header.'})

    @app.exception_handler(HTTPException)
    async def http_error(request,exc):
        detail=exc.detail if isinstance(exc.detail,dict) else {'code':'http_error','message':str(exc.detail)}
        return error(exc.status_code,detail.get('code','http_error'),detail.get('message','Request failed.'),getattr(request.state,'request_id',None),exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        return error(422,'invalid_request','Use multipart/form-data with one file field named file; model must be original, adapted or lowres.',getattr(request.state,'request_id',None))

    @app.get('/health',tags=['Status'])
    async def health(request: Request):
        engine=request.app.state.detector
        return dict(status='ok',ready=True,api_version=__version__,model_id=MODEL_ID,device=engine.device,pending=request.app.state.pending,max_image_bytes=settings.max_image_bytes,max_pixels=settings.max_pixels)

    @app.get('/',response_class=HTMLResponse,include_in_schema=False)
    @app.get('/demo',response_class=HTMLResponse,include_in_schema=False)
    async def demo():return HTMLResponse((ROOT/'web_demo.html').read_text(encoding='utf8'))

    @app.get('/v1/model',dependencies=[Depends(authorized)],tags=['Model'])
    async def model_info(request: Request):return request.app.state.detector.metadata()

    @app.get('/v1/web-search/status',dependencies=[Depends(authorized)],tags=['Web search'])
    async def web_search_status(request: Request):return request.app.state.web_search.status()

    @app.post('/v1/predict',response_model=Prediction,dependencies=[Depends(authorized)],responses={400:{'description':'Empty/corrupt image or unexpected fields'},401:{'description':'Invalid API key'},403:{'description':'Disallowed browser origin'},413:{'description':'Body/image/pixel limit'},415:{'description':'Unsupported format or animation'},429:{'description':'Server busy; retry later'}},tags=['Prediction'])
    async def predict(request: Request,file: UploadFile=File(...),model: Literal['original','adapted','lowres']='lowres',web_search: bool=False):
        start=time.perf_counter();request_id=request.state.request_id
        try:
            form=await request.form()
            if len(form.multi_items())!=1:raise HTTPException(400,detail={'code':'unexpected_form_fields','message':'Submit exactly one file field named file.'})
            raw=await file.read(settings.max_image_bytes+1)
        finally:await file.close()
        if not raw:raise HTTPException(400,detail={'code':'empty_image','message':'The image file is empty.'})
        if len(raw)>settings.max_image_bytes:raise HTTPException(413,detail={'code':'file_too_large','message':f'Image exceeds {settings.max_image_bytes} bytes.'})
        if request.app.state.pending>=settings.max_pending:raise HTTPException(429,detail={'code':'server_busy','message':'Too many pending images. Retry after 1 second.'},headers={'Retry-After':'1'})
        request.app.state.pending+=1;acquired=False;queued=time.perf_counter()
        try:
            try:await asyncio.wait_for(request.app.state.semaphore.acquire(),timeout=settings.queue_timeout);acquired=True
            except asyncio.TimeoutError:raise HTTPException(429,detail={'code':'server_busy','message':'Inference queue timeout. Retry after 1 second.'},headers={'Retry-After':'1'})
            queue_ms=(time.perf_counter()-queued)*1000
            try:result=await asyncio.to_thread(request.app.state.detector.predict_bytes,raw)
            except ImageError as exc:raise HTTPException(exc.status,detail={'code':exc.code,'message':exc.message})
            except Exception:
                LOGGER.exception('Prediction failed request_id=%s',request_id)
                raise HTTPException(500,detail={'code':'inference_failed','message':'Local inference failed. Check the server terminal.'})
        finally:
            if acquired:request.app.state.semaphore.release()
            request.app.state.pending-=1
        def score(value):return dict(score_ai=value,prediction=int(value>=.5),label='ai_generated' if value>=.5 else 'real')
        scores={k:score(v) for k,v in result['scores'].items()}
        web_usage=await request.app.state.web_search.search(raw,requested=web_search)
        return dict(api_version=__version__,request_id=request_id,model_id=MODEL_ID,selected_model=model,result=scores[model],scores=scores,threshold=.5,score_kind='uncalibrated_model_score',cached=result['cached'],image=result['image'],timing=dict(queue_ms=queue_ms,preprocess_ms=result['preprocess_ms'],inference_ms=result['inference_ms'],total_ms=(time.perf_counter()-start)*1000),notice=NOTICE,web_usage=web_usage)

    app.add_middleware(RequestGate,settings=settings)
    app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins,allow_origin_regex=settings.cors_regex,allow_methods=['GET','POST','OPTIONS'],allow_headers=['X-API-Key','Content-Type'],expose_headers=['Retry-After'],allow_credentials=False)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=list(settings.allowed_hosts),www_redirect=False)
    return app
