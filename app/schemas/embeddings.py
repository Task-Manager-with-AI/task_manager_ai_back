from typing import List

from pydantic import BaseModel, Field


class EmbeddingsRequest(BaseModel):
    texts: List[str] = Field(default_factory=list)


class EmbeddingsData(BaseModel):
    vectors: List[List[float]] = Field(default_factory=list)
    model: str
    dim: int


class EmbeddingsResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: EmbeddingsData
