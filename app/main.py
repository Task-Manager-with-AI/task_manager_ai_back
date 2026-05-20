from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.transcription import router as transcription_router
from app.api.v1.minutes import router as minutes_router
from app.api.v1.suggestions import router as suggestions_router
from app.api.v1.analysis import router as analysis_router

app = FastAPI(
    title="Task Manager AI Service",
    version="1.2.0",
    description=(
        "AI features for the agile task manager — Sprint 2.\n\n"
        "Includes: transcription, meeting minutes, task suggestions, "
        "meeting type detection (Daily/Sprint Planning/Regular), "
        "Daily Scrum analysis with blocker detection, Sprint Planning analysis, "
        "and automatic Kanban update detection."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(transcription_router, prefix="/api/v1")
app.include_router(minutes_router, prefix="/api/v1")
app.include_router(suggestions_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
