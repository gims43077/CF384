"""Exact CF384 preprocessing, one frozen feature pass, three linear heads."""
import copy
import gc
import hashlib
import io
import threading
import time
import warnings
from collections import OrderedDict
from pathlib import Path
import numpy as np
import timm
import torch
from PIL import Image,ImageOps,UnidentifiedImageError
from safetensors.torch import load_file
from torchvision import transforms as T

BASE_SHA256='b89f36275f3bf5e2b040eee36597a8f19db051bff9a473a9cf7b2466284fb387'
HEAD_SHA256='c7595c7b504e1195effe31600e8bebe3527812d9c5a93560bc71d9e5e2b42adb'
LOWRES_HEAD_SHA256='4d4b0afa8257172a42740a01fd81d353dc8e232d670bd43d4eede2a99be54886'
FORMATS=('JPEG','PNG','WEBP','TIFF','BMP')
MODEL_ID='cf384-l2sp-aug-lowres-default-20261119'
NOTICE='Research model score, not a calibrated probability or proof of image authenticity.'

class ImageError(Exception):
    def __init__(self,code,message,status=400):super().__init__(message);self.code=code;self.message=message;self.status=status

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def choose_device(name):
    if name=='auto':return 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    if name=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA requested but unavailable. Use --device cpu or auto.')
    if name=='mps' and not torch.backends.mps.is_available():raise RuntimeError('MPS requested but unavailable. Use --device cpu or auto.')
    return name

class Detector:
    def __init__(self,settings):
        self.settings=settings;self.device=choose_device(settings.device);self.lock=threading.Lock();self.cache=OrderedDict()
        base=Path(settings.model_dir)/'cf384.safetensors';head=Path(settings.model_dir)/'l2sp_aug_mean.npz';lowres_head=Path(settings.model_dir)/'l2sp_aug_lowres_mean.npz'
        for path,expected in [(base,BASE_SHA256),(head,HEAD_SHA256),(lowres_head,LOWRES_HEAD_SHA256)]:
            if not path.is_file():raise FileNotFoundError(f'Model missing: {path}. Run python prepare_models.py or use the complete bundle.')
            if sha256_file(path)!=expected:raise ValueError(f'Model SHA256 mismatch: {path.name}; refusing incorrect weights.')
        torch.set_num_threads(settings.threads)
        self.model=timm.create_model('vit_small_patch16_384.augreg_in21k_ft_in1k',pretrained=False,num_classes=1)
        state=load_file(str(base));self.model.load_state_dict({k.removeprefix('vit.'):v for k,v in state.items()},strict=True)
        del state;gc.collect();self.model.requires_grad_(False);self.model.eval().to(self.device)
        with np.load(head,allow_pickle=False) as arrays:
            w=arrays['weight'].copy();b=arrays['bias'].copy()
        if w.shape!=(384,) or b.shape!=(1,) or not np.isfinite(w).all() or not np.isfinite(b).all():raise ValueError('Invalid adapted head')
        self.weight=torch.tensor(w,dtype=torch.float32,device=self.device);self.bias=torch.tensor(b,dtype=torch.float32,device=self.device)
        with np.load(lowres_head,allow_pickle=False) as arrays:lw=arrays['weight'].copy();lb=arrays['bias'].copy()
        if lw.shape!=(384,) or lb.shape!=(1,) or not np.isfinite(lw).all() or not np.isfinite(lb).all():raise ValueError('Invalid low-resolution head')
        self.lowres_weight=torch.tensor(lw,dtype=torch.float32,device=self.device);self.lowres_bias=torch.tensor(lb,dtype=torch.float32,device=self.device)
        self.transform=T.Compose([T.Resize(440),T.CenterCrop(384),T.ToTensor(),T.Normalize([.485,.456,.406],[.229,.224,.225])])

    def metadata(self):
        return dict(model_id=MODEL_ID,default_model='lowres',architecture='ViT-S/16',feature_dim=384,adaptation='L2-SP + fixed postprocessing augmentation; arithmetic mean of 4 fold heads',lowres_adaptation='Additional two160-300px downsampling training views; same frozen backbone; separate 4-fold mean head',device=self.device,weights_frozen=True,threshold=.5,score_kind='uncalibrated_model_score',available_models=['original','adapted','lowres'],base_sha256=BASE_SHA256,head_sha256=HEAD_SHA256,lowres_head_sha256=LOWRES_HEAD_SHA256,
          preprocessing=['EXIF orientation','RGB','whole image bilinear warp to 512x512','JPEG95, subsampling=2','Resize short side 440 bilinear','CenterCrop384','ImageNet normalization'],notice=NOTICE)

    def decode(self,raw):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as opened:
                    fmt=opened.format
                    if fmt not in FORMATS:raise ImageError('unsupported_format',f'Supported formats: {", ".join(FORMATS)}. SVG/GIF/HEIC/AVIF are not accepted.',415)
                    if opened.width*opened.height>self.settings.max_pixels:raise ImageError('image_too_large',f'Image exceeds {self.settings.max_pixels} pixels.',413)
                    if getattr(opened,'n_frames',1)>1:raise ImageError('animated_or_multipage','Animated or multipage images are not supported. Submit one still frame.',415)
                    im=ImageOps.exif_transpose(opened).convert('RGB');im.load()
        except ImageError:raise
        except (Image.DecompressionBombWarning,Image.DecompressionBombError):raise ImageError('image_too_large','Image exceeds the safe pixel limit.',413)
        except UnidentifiedImageError:raise ImageError('unsupported_format','Cannot identify this image. Submit a JPEG, PNG, WEBP, TIFF or BMP file.',415)
        except (OSError,ValueError,SyntaxError):raise ImageError('invalid_image','The image is corrupt or incomplete.',400)
        return im,dict(width=im.width,height=im.height,format=fmt)

    def predict_bytes(self,raw):
        if not raw:raise ImageError('empty_image','The image file is empty.',400)
        if len(raw)>self.settings.max_image_bytes:raise ImageError('file_too_large',f'Image exceeds {self.settings.max_image_bytes} bytes.',413)
        digest=hashlib.sha256(raw).hexdigest()
        with self.lock:
            if digest in self.cache:
                saved=self.cache.pop(digest);self.cache[digest]=saved
                out=copy.deepcopy(saved);out.update(cached=True,inference_ms=0.0,preprocess_ms=0.0);return out
            start=time.perf_counter();im,image=self.decode(raw)
            common=im.resize((512,512),Image.Resampling.BILINEAR);stream=io.BytesIO();common.save(stream,format='JPEG',quality=95,subsampling=2);stream.seek(0)
            with Image.open(stream) as common_image:x=self.transform(common_image.convert('RGB')).unsqueeze(0).to(self.device)
            preprocess_ms=(time.perf_counter()-start)*1000;start=time.perf_counter()
            with torch.inference_mode():
                f=self.model.forward_head(self.model.forward_features(x),pre_logits=True)
                original=float(self.model.head(f).sigmoid().cpu().item());adapted=float((f@self.weight+self.bias).sigmoid().cpu().item());lowres=float((f@self.lowres_weight+self.lowres_bias).sigmoid().cpu().item())
            out=dict(image={**image,'sha256':digest,'bytes':len(raw)},scores={'original':original,'adapted':adapted,'lowres':lowres},cached=False,inference_ms=(time.perf_counter()-start)*1000,preprocess_ms=preprocess_ms)
            if self.settings.cache_size:
                self.cache[digest]=copy.deepcopy(out)
                while len(self.cache)>self.settings.cache_size:self.cache.popitem(last=False)
            return out

    def close(self):
        self.cache.clear();self.model.to('cpu')
        if self.device=='mps':torch.mps.empty_cache()
        if self.device=='cuda':torch.cuda.empty_cache()
