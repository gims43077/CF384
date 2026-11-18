"""Run the standalone API. One process, loopback by default, no cloud resources."""
import argparse
from pathlib import Path
from cf384_api.config import ROOT,Settings,read_or_create_key

def main():
    p=argparse.ArgumentParser(description='CF384 local image inference server')
    p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8000)
    p.add_argument('--device',choices=['cpu','mps','cuda','auto'],default='cpu');p.add_argument('--threads',type=int,default=4)
    p.add_argument('--models',type=Path,default=ROOT/'models');p.add_argument('--key-file',type=Path,default=ROOT/'.runtime/api_key.txt')
    p.add_argument('--extension-id',action='append',default=[],help='Allow only these Chrome extension IDs; repeat flag for multiple IDs')
    p.add_argument('--allowed-origin',action='append',default=[],help='Additional exact browser origins')
    p.add_argument('--allowed-host',action='append',default=[],help='Additional Host header values, e.g. LAN IP')
    p.add_argument('--cache-size',type=int,default=128);p.add_argument('--max-image-mb',type=int,default=10)
    a=p.parse_args()
    key=read_or_create_key(a.key_file)
    settings=Settings(api_key=key,model_dir=a.models.resolve(),device=a.device,threads=a.threads,cache_size=a.cache_size,max_image_bytes=a.max_image_mb*1024*1024,extension_ids=tuple(a.extension_id),allowed_origins=tuple([f'http://127.0.0.1:{a.port}',f'http://localhost:{a.port}']+a.allowed_origin),allowed_hosts=tuple(['127.0.0.1','localhost']+a.allowed_host))
    from cf384_api.app import create_app
    import uvicorn
    print(f'API: http://{a.host}:{a.port}   Swagger UI: http://127.0.0.1:{a.port}/docs',flush=True)
    print(f'API key file: {a.key_file.resolve()} (or CF384_API_KEY environment override). Keep the key in the extension settings.',flush=True)
    print('Model loads once at startup. Close with Ctrl+C. Uploads are not retained as image files.',flush=True)
    uvicorn.run(create_app(settings),host=a.host,port=a.port,workers=1,limit_concurrency=32,timeout_keep_alive=5,log_level='info')

if __name__=='__main__':main()
