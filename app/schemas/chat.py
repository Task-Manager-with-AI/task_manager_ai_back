from typing import List

from pydantic import BaseModel, Field


class ChatSummaryRequest(BaseModel):
    transcript: str
    language: str = "es"


class ChatSummaryData(BaseModel):
    summary: List[str] = Field(default_factory=list)


class ChatSummaryResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: ChatSummaryData
