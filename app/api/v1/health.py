from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"success": True, "message": "OK", "data": {"status": "ok"}}


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
