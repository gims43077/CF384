"""Portable Python API client; reads the local key file by default."""
import argparse,json,mimetypes,os,urllib.request,urllib.error,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def predict(image,base_url='http://127.0.0.1:8000',api_key=None,model='lowres',timeout=60,web_search=False):
    if model not in ('original','adapted','lowres'):raise ValueError('Invalid model')
    path=Path(image);raw=path.read_bytes();boundary='cf384-'+uuid.uuid4().hex
    # Fixed multipart filename avoids quoting/encoding issues with user-supplied names.
    content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="image"\r\nContent-Type: {content_type}\r\n\r\n'.encode()+raw+f'\r\n--{boundary}--\r\n'.encode())
    key=api_key or os.environ.get('CF384_API_KEY') or (ROOT/'.runtime/api_key.txt').read_text(encoding='utf8').strip()
    req=urllib.request.Request(base_url.rstrip('/')+'/v1/predict?model='+model+'&web_search='+str(bool(web_search)).lower(),data=body,headers={'X-API-Key':key,'Content-Type':'multipart/form-data; boundary='+boundary},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
    except urllib.error.HTTPError as exc:
        try:message=json.loads(exc.read())
        except ValueError:message={'error':{'message':str(exc)}}
        raise RuntimeError(f'HTTP {exc.code}: {message}') from exc

def main():
    p=argparse.ArgumentParser();p.add_argument('image',nargs='?');p.add_argument('--base-url',default='http://127.0.0.1:8000');p.add_argument('--model',choices=['original','adapted','lowres'],default='lowres');p.add_argument('--key-file',type=Path,default=ROOT/'.runtime/api_key.txt');p.add_argument('--show-key',action='store_true');p.add_argument('--web-search',action='store_true',help='Upload to configured reverse-search provider; may consume credits');a=p.parse_args()
    key=os.environ.get('CF384_API_KEY') or a.key_file.read_text(encoding='utf8').strip()
    if a.show_key:print(key);return
    if not a.image:p.error('image is required unless --show-key is used')
    print(json.dumps(predict(a.image,a.base_url,key,a.model,web_search=a.web_search),indent=2,ensure_ascii=False))

if __name__=='__main__':main()
