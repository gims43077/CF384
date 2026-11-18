"""Public regression tests use only generated images and a per-run random key."""
import io,secrets,sys
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cf384_api.app import create_app
from cf384_api.config import Settings
from cf384_api.engine import Detector
KEY=secrets.token_urlsafe(32)

def image_bytes(side=160):
    buffer=io.BytesIO();Image.new('RGB',(side,side),(47,103,155)).save(buffer,format='PNG');return buffer.getvalue()

@pytest.fixture(scope='module')
def client():
    if not (ROOT/'models/cf384.safetensors').exists():pytest.skip('Download official backbone: python prepare_models.py --download')
    settings=Settings(api_key=KEY,allowed_hosts=('testserver',))
    with TestClient(create_app(settings,Detector(settings))) as c:yield c

def test_key_hidden_in_settings_and_origin_limits():
    settings=Settings(api_key=KEY,extension_ids=('a'*32,))
    assert KEY not in repr(settings)
    assert settings.permits_origin('chrome-extension://'+'a'*32)
    assert not settings.permits_origin('https://example.invalid')

def test_health_and_schema(client):
    assert client.get('/health').json()['ready']
    assert '/v1/predict' in client.get('/openapi.json').json()['paths']

def test_authentication(client):
    assert client.get('/v1/model').status_code==401
    assert client.get('/v1/model',headers={'X-API-Key':KEY}).status_code==200

def test_synthetic_image_modes_and_cache(client):
    image=image_bytes()
    first=client.post('/v1/predict?model=lowres',headers={'X-API-Key':KEY},files={'file':('synthetic.png',image,'image/png')})
    assert first.status_code==200,first.text
    data=first.json();assert data['selected_model']=='lowres' and data['image']['width']==160
    assert set(data['scores'])=={'original','adapted','lowres'}
    for value in data['scores'].values():assert 0<=value['score_ai']<=1
    second=client.post('/v1/predict?model=original',headers={'X-API-Key':KEY},files={'file':('synthetic.png',image,'image/png')}).json()
    assert second['cached'] and second['scores']==data['scores']

def test_invalid_input(client):
    r=client.post('/v1/predict',headers={'X-API-Key':KEY},files={'file':('bad.png',b'not image','image/png')})
    assert r.status_code==415
    assert client.post('/v1/predict',headers={'X-API-Key':KEY}).status_code==422

def test_cors_and_origin_checks(client):
    origin='chrome-extension://'+'a'*32
    r=client.options('/v1/predict',headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'x-api-key'})
    assert r.status_code==200 and r.headers['access-control-allow-origin']==origin
    assert client.post('/v1/predict',headers={'Origin':'https://example.invalid','X-API-Key':KEY},content=b'bad').status_code==403

def test_host_header(client):
    assert client.get('/health',headers={'Host':'example.invalid'}).status_code==400
