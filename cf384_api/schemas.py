from typing import Literal
from pydantic import BaseModel,Field

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
