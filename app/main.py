import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.analysis import router as analysis_router
from app.api.v1.health import router as health_router
from app.api.v1.minutes import router as minutes_router
from app.api.v1.suggestions import router as suggestions_router
from app.api.v1.transcription import router as transcription_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.services import whisper_service

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.WHISPER_PRELOAD_ON_STARTUP:
        logger.info(
            "Preloading Whisper on startup (model=%s)...",
            settings.LOCAL_WHISPER_MODEL,
        )
        try:
            await asyncio.to_thread(whisper_service.preload_whisper_model)
        except Exception:
            logger.exception("Whisper preload failed; will retry on first /transcribe")
    else:
        logger.info("Whisper preload disabled (WHISPER_PRELOAD_ON_STARTUP=false)")
    yield


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
    lifespan=lifespan,
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
