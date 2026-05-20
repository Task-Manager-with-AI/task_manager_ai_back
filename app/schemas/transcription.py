from pydantic import BaseModel


class TranscriptionData(BaseModel):
    transcript: str
    language: str
    duration_seconds: float


class TranscriptionResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: TranscriptionData
