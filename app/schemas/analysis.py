from typing import List, Optional
from pydantic import BaseModel, Field


# ─── Detect meeting type ─────────────────────────────────────────────────────

class DetectTypeRequest(BaseModel):
    transcript: str
    meeting_title: str = ""
    participants: List[str] = Field(default_factory=list)
    language: str = "es"


class DetectTypeData(BaseModel):
    meeting_type: str  # "DAILY" | "SPRINT_PLANNING" | "REGULAR"
    confidence: float
    reason: str


class DetectTypeResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: DetectTypeData


# ─── Daily standup analysis ──────────────────────────────────────────────────

class AnalyzeDailyRequest(BaseModel):
    transcript: str
    participants: List[str] = Field(default_factory=list)
    language: str = "es"


class DailyEntryData(BaseModel):
    participant_name: str
    yesterday: str
    today: str
    blockers: List[str] = Field(default_factory=list)


class AnalyzeDailyData(BaseModel):
    entries: List[DailyEntryData] = Field(default_factory=list)
    overall_blockers: List[str] = Field(default_factory=list)
    sprint_health: str = "GREEN"  # "GREEN" | "YELLOW" | "RED"


class AnalyzeDailyResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: AnalyzeDailyData


# ─── Sprint planning analysis ────────────────────────────────────────────────

class AnalyzeSprintRequest(BaseModel):
    transcript: str
    meeting_title: str = ""
    participants: List[str] = Field(default_factory=list)
    project_members: List[dict] = Field(default_factory=list)
    language: str = "es"


class SprintTaskData(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "MEDIUM"
    suggested_responsible_id: Optional[str] = None
    story_points: Optional[int] = None


class AnalyzeSprintData(BaseModel):
    sprint_goal: str = ""
    sprint_duration_weeks: Optional[int] = None
    user_stories: List[str] = Field(default_factory=list)
    tasks: List[SprintTaskData] = Field(default_factory=list)


class AnalyzeSprintResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: AnalyzeSprintData


# ─── Kanban auto-update detection ────────────────────────────────────────────

class ExistingTask(BaseModel):
    id: str
    title: str
    column_title: str


class DetectKanbanUpdatesRequest(BaseModel):
    transcript: str
    existing_tasks: List[ExistingTask] = Field(default_factory=list)
    language: str = "es"


class KanbanUpdateData(BaseModel):
    task_id: Optional[str] = None
    task_title: str
    new_status: str  # "DONE" | "IN_PROGRESS" | "BLOCKED"
    mentioned_by: str
    confidence: float
    notes: Optional[str] = None


class DetectKanbanUpdatesData(BaseModel):
    updates: List[KanbanUpdateData] = Field(default_factory=list)


class DetectKanbanUpdatesResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: DetectKanbanUpdatesData
