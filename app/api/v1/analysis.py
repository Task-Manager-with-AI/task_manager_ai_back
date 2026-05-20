from fastapi import APIRouter, HTTPException

from app.schemas.analysis import (
    AnalyzeDailyRequest,
    AnalyzeDailyResponse,
    AnalyzeSprintRequest,
    AnalyzeSprintResponse,
    DetectKanbanUpdatesRequest,
    DetectKanbanUpdatesResponse,
    DetectTypeRequest,
    DetectTypeResponse,
)
from app.services import llm_service

router = APIRouter(tags=["analysis"])


@router.post("/detect-type", response_model=DetectTypeResponse, summary="Detect meeting type from transcript")
async def detect_meeting_type(body: DetectTypeRequest):
    """
    Classify a meeting transcript as DAILY, SPRINT_PLANNING, or REGULAR.
    """
    try:
        data = await llm_service.detect_meeting_type(
            transcript=body.transcript,
            meeting_title=body.meeting_title,
            participants=body.participants,
            language=body.language,
        )
        return DetectTypeResponse(data=data)  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze-daily", response_model=AnalyzeDailyResponse, summary="Analyze Daily Scrum standup transcript")
async def analyze_daily(body: AnalyzeDailyRequest):
    """
    Extract per-participant answers to the 3 Daily Scrum questions and detect blockers/impediments.
    """
    try:
        data = await llm_service.analyze_daily(
            transcript=body.transcript,
            participants=body.participants,
            language=body.language,
        )
        return AnalyzeDailyResponse(data=data)  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze-sprint", response_model=AnalyzeSprintResponse, summary="Analyze Sprint Planning transcript")
async def analyze_sprint(body: AnalyzeSprintRequest):
    """
    Extract sprint goal, user stories, and task assignments from a Sprint Planning transcript.
    """
    try:
        data = await llm_service.analyze_sprint_planning(
            transcript=body.transcript,
            meeting_title=body.meeting_title,
            participants=body.participants,
            project_members=body.project_members,
            language=body.language,
        )
        return AnalyzeSprintResponse(data=data)  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/detect-kanban-updates",
    response_model=DetectKanbanUpdatesResponse,
    summary="Detect task status changes mentioned in a meeting",
)
async def detect_kanban_updates(body: DetectKanbanUpdatesRequest):
    """
    Detect when participants mention completing, starting, or blocking tasks.
    Returns matched task IDs and suggested new statuses so the backend can apply Kanban updates.
    """
    try:
        existing = [t.model_dump() for t in body.existing_tasks]
        data = await llm_service.detect_kanban_updates(
            transcript=body.transcript,
            existing_tasks=existing,
            language=body.language,
        )
        return DetectKanbanUpdatesResponse(data=data)  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
