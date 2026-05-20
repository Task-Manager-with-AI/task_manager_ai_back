from fastapi import APIRouter, HTTPException

from app.schemas.minutes import (
    Agreement,
    MinutesData,
    MinutesRequest,
    MinutesResponse,
)
from app.services import llm_service

router = APIRouter()


@router.post("/minutes", response_model=MinutesResponse)
async def generate_minutes(body: MinutesRequest):
    try:
        parsed = await llm_service.generate_minutes(
            transcript=body.transcript,
            meeting_title=body.meeting_title,
            participants=body.participants,
            language=body.language,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Minute generation failed: {exc}")

    return MinutesResponse(
        data=MinutesData(
            summary=parsed.get("summary", ""),
            key_points=parsed.get("key_points", []) or [],
            agreements=[Agreement(**a) for a in parsed.get("agreements", []) or []],
        )
    )
