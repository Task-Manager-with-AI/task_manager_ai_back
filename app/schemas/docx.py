from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field


class DocxJobRequest(BaseModel):
    jobId: str
    documentId: str
    type: Literal["IMPORT_DOCX", "EXPORT_DOCX"]
    inputAssetId: Optional[str] = None
    sourceVersionId: Optional[str] = None
    requestedFileName: Optional[str] = None
    inputFileBase64: Optional[str] = None
    sourcePlainText: Optional[str] = None
    sourceTitle: Optional[str] = None
    callbackUrl: str
    callbackSecret: str


class DocxJobResponse(BaseModel):
    success: bool = True
    message: str = "Accepted"
    data: Dict[str, Any] = Field(default_factory=dict)


class DocxJobStatusResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Dict[str, Any] = Field(default_factory=dict)
