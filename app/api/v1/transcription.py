from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.schemas.transcription import TranscriptionData, TranscriptionResponse
from app.services import whisper_service

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    audio_file: UploadFile = File(...),
    language: str = Form("es"),
):
    try:
        transcript, detected_lang, duration = await whisper_service.transcribe(
            audio_file, language
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")

    return TranscriptionResponse(
        data=TranscriptionData(
            transcript=transcript,
            language=detected_lang,
            duration_seconds=duration,
        )
    )
