"""Store an existing SerpApi Free-plan key locally. Does not purchase credits or call SerpApi Free-plan."""
import getpass
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def store_key(key,path):
    if len(key.strip())<8 or any(c in key for c in ('\n','\r')):raise ValueError('Enter a valid existing provider key')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():raise ValueError('Refusing a symlink key path')
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    try:
        try:os.fchmod(fd,0o600)
        except (AttributeError,OSError):pass
        with os.fdopen(fd,'w',encoding='utf8') as stream:stream.write(key.strip()+'\n')
    except Exception:
        try:os.close(fd)
        except OSError:pass
        raise

def main():
    print('Use an existing SerpApi Free-plan API key. No purchase or search is performed.')
    key=getpass.getpass('SerpApi Free-plan API key (hidden): ')
    store_key(key,ROOT/'.runtime/serpapi_api_key.txt')
    print('Provider key saved under .runtime. Do not share this folder.')
    print('To enable free-plan searches, set CF384_WEB_SEARCH_ENABLED=1 and restart.')

if __name__=='__main__':main()
