import os
import re
import secrets
from dataclasses import dataclass,field
from pathlib import Path
from typing import Tuple

ROOT=Path(__file__).resolve().parents[1]

def read_provider_key():
    override=os.environ.get('TINEYE_API_KEY')
    if override:return override
    path=ROOT/'.runtime/tineye_api_key.txt'
    return path.read_text(encoding='utf8').strip() if path.exists() else ''

def read_or_create_key(path=ROOT/'.runtime/api_key.txt'):
    override=os.environ.get('CF384_API_KEY')
    if override:return override
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        # Exclusive create avoids two startup processes overwriting the key.
        try:
            with path.open('x',encoding='utf8') as stream:stream.write(secrets.token_urlsafe(32)+'\n')
        except FileExistsError:pass
        try:path.chmod(0o600)
        except OSError:pass
    value=path.read_text(encoding='utf8').strip()
    if len(value)<16:raise ValueError('API key must contain at least 16 characters. Check .runtime/api_key.txt.')
    return value

@dataclass(frozen=True)
class Settings:
    api_key: str=field(repr=False)
    model_dir: Path=ROOT/'models'
    device: str='cpu'
    threads: int=4
    max_image_bytes: int=10*1024*1024
    max_pixels: int=40_000_000
    cache_size: int=128
    max_pending: int=8
    queue_timeout: float=5.0
    extension_ids: Tuple[str,...]=()
    allowed_origins: Tuple[str,...]=('http://127.0.0.1:8000','http://localhost:8000')
    allowed_hosts: Tuple[str,...]=('127.0.0.1','localhost')
    tineye_api_key: str=field(default_factory=read_provider_key,repr=False)
    web_search_enabled: bool=field(default_factory=lambda:os.environ.get('CF384_WEB_SEARCH_ENABLED')=='1')
    web_search_timeout: float=20.0
    web_search_cache_ttl: float=3600.0
    web_search_max_calls: int=20

    def __post_init__(self):
        if len(self.api_key)<16:raise ValueError('API key must be at least 16 characters')
        if not 1<=self.web_search_timeout<=30 or not 1<=self.web_search_cache_ttl<=86400 or not 1<=self.web_search_max_calls<=1000:raise ValueError('Invalid web search limits')
        if any(c in self.tineye_api_key for c in ('\n','\r')):raise ValueError('Invalid provider key')
        if self.device not in ('cpu','mps','cuda','auto'):raise ValueError('device must be cpu/mps/cuda/auto')
        if not 1<=self.threads<=32:raise ValueError('threads must be 1..32')
        if self.cache_size<0 or self.max_image_bytes<1 or self.max_pixels<1 or self.max_pending<1 or self.queue_timeout<=0:raise ValueError('Invalid resource limit')
        for extension_id in self.extension_ids:
            if not re.fullmatch('[a-p]{32}',extension_id):raise ValueError('Chrome extension ID must be 32 lowercase letters a-p')

    @property
    def cors_origins(self):return list(self.allowed_origins)+['chrome-extension://'+i for i in self.extension_ids]

    @property
    def cors_regex(self):return None if self.extension_ids else r'chrome-extension://[a-p]{32}'

    def permits_origin(self,origin):
        return origin in self.cors_origins or bool(self.cors_regex and re.fullmatch(self.cors_regex,origin))
