from typing import Literal,Optional
from pydantic import BaseModel,Field

class WebBacklink(BaseModel):
    page_url: str
    image_url: Optional[str]=None
    crawl_date: Optional[str]=None

class WebMatch(BaseModel):
    image_url: Optional[str]=None
    domain: Optional[str]=None
    provider_score: Optional[float]=None
    match_kind: str="provider_exact_match"
    title: Optional[str]=None
    thumbnail_url: Optional[str]=None
    backlinks: list[WebBacklink]

class WebUsage(BaseModel):
    status: Literal['not_requested','disabled','not_configured','matches_found','no_matches','error','rate_limited','blocked']
    provider: str
    searched_at: Optional[str]=None
    cached: bool=False
    matches: list[WebMatch]=Field(default_factory=list)
    returned_matches: int=0
    provider_matches_in_page: Optional[int]=None
    error_code: Optional[str]=None
    notice: str

class Score(BaseModel):
    score_ai: float=Field(ge=0,le=1)
    prediction: Literal[0,1]
    label: Literal['real','ai_generated']

class ImageInfo(BaseModel):
    width: int
    height: int
    format: str
    sha256: str
    bytes: int

class Timings(BaseModel):
    queue_ms: float
    preprocess_ms: float
    inference_ms: float
    total_ms: float

class Prediction(BaseModel):
    api_version: str
    request_id: str
    model_id: str
    selected_model: Literal['original','adapted','lowres']
    result: Score
    scores: dict[str,Score]
    threshold: float
    score_kind: str
    cached: bool
    image: ImageInfo
    timing: Timings
    notice: str
    web_usage: WebUsage
