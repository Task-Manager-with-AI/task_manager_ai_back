from typing import List
from pydantic import BaseModel, Field


class MinutesRequest(BaseModel):
    transcript: str
    meeting_title: str = ""
    participants: List[str] = Field(default_factory=list)
    language: str = "es"


class Agreement(BaseModel):
    order: int
    text: str


class MinutesData(BaseModel):
    summary: str
    key_points: List[str] = Field(default_factory=list)
    agreements: List[Agreement] = Field(default_factory=list)


class MinutesResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: MinutesData
