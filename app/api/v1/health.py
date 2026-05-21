from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.services import whisper_service

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "success": True,
        "message": "OK",
        "data": {
            "status": "ok",
            "whisper_model": settings.LOCAL_WHISPER_MODEL,
            "whisper_loaded": whisper_service.is_model_loaded(),
            "whisper_load_seconds": whisper_service.model_load_seconds(),
        },
    }


@router.get("/info")
def service_info():
    return {
        "success": True,
        "message": "OK",
        "data": {
            "name": "Task Manager AI Service",
            "version": "1.0.0",
            "description": "AI features for the agile task manager (Sprint 2)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
