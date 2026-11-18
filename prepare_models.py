"""Verify bundled small heads; optionally download only the official backbone."""
import argparse,urllib.request
from pathlib import Path
from cf384_api.config import ROOT
from cf384_api.engine import BASE_SHA256,HEAD_SHA256,LOWRES_HEAD_SHA256,sha256_file
REVISION='6076002bf0d9dd37537f965ee2f06f826c333b61'
URL=f'https://huggingface.co/OwensLab/commfor-model-384/resolve/{REVISION}/model.safetensors'

def main():
    p=argparse.ArgumentParser();p.add_argument('--download',action='store_true');a=p.parse_args()
    folder=ROOT/'models';folder.mkdir(exist_ok=True)
    for name,digest in [('cf384.safetensors',BASE_SHA256),('l2sp_aug_mean.npz',HEAD_SHA256),('l2sp_aug_lowres_mean.npz',LOWRES_HEAD_SHA256)]:
        dest=folder/name
        if not dest.exists():
            if name!='cf384.safetensors' or not a.download:raise FileNotFoundError(f'Missing {name}. Restore small heads from this repository; use --download for the official backbone.')
            temp=dest.with_suffix('.download')
            try:
                print('Downloading official CF384 backbone...');urllib.request.urlretrieve(URL,temp)
                if sha256_file(temp)!=digest:raise ValueError('Downloaded backbone SHA256 mismatch')
                temp.replace(dest)
            finally:
                if temp.exists():temp.unlink()
        if sha256_file(dest)!=digest:raise ValueError(f'Incorrect model checksum: {name}')
        print('Verified:',name)

if __name__=='__main__':main()
