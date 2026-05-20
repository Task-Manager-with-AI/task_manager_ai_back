from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ProjectMember(BaseModel):
    id: str
    name: str


class SuggestionsRequest(BaseModel):
    agreements: List[str] = Field(default_factory=list)
    project_members: List[ProjectMember] = Field(default_factory=list)
    language: str = "es"


class SuggestionItem(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    suggested_responsible_id: Optional[str] = None


class SuggestionsData(BaseModel):
    suggestions: List[SuggestionItem] = Field(default_factory=list)


class SuggestionsResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: SuggestionsData
