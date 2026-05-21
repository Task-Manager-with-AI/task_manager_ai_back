import asyncio
import logging
import os
import tempfile
import time
from typing import Tuple

import aiofiles
from fastapi import UploadFile, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

_local_model = None
_model_load_seconds: float | None = None


def _apply_hf_token() -> None:
    if settings.HF_TOKEN:
        os.environ["HF_TOKEN"] = settings.HF_TOKEN


def _load_whisper_model():
    global _local_model, _model_load_seconds
    if _local_model is not None:
        return _local_model

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="faster-whisper is not installed. Run: pip install faster-whisper",
        ) from exc

    _apply_hf_token()
    model_name = settings.LOCAL_WHISPER_MODEL
    logger.info(
        "Loading Whisper model '%s' (device=%s, compute=%s)...",
        model_name,
        settings.LOCAL_WHISPER_DEVICE,
        settings.LOCAL_WHISPER_COMPUTE_TYPE,
    )
    started = time.perf_counter()
    _local_model = WhisperModel(
        model_name,
        device=settings.LOCAL_WHISPER_DEVICE,
        compute_type=settings.LOCAL_WHISPER_COMPUTE_TYPE,
    )
    _model_load_seconds = time.perf_counter() - started
    logger.info("Whisper model ready in %.1fs", _model_load_seconds)
    return _local_model


def preload_whisper_model() -> None:
    """Load Whisper into memory (call at startup or Docker build)."""
    _load_whisper_model()


def is_model_loaded() -> bool:
    return _local_model is not None


def model_load_seconds() -> float | None:
    return _model_load_seconds


async def _save_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1] or ".webm"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    async with aiofiles.open(path, "wb") as f:
        while chunk := await upload.read(1024 * 1024):
            await f.write(chunk)
    return path


def _transcribe_file(path: str, language: str) -> Tuple[str, str, float]:
    model = _load_whisper_model()
    lang = language or settings.DEFAULT_LANGUAGE
    segments, info = model.transcribe(
        path,
        language=lang,
        beam_size=settings.LOCAL_WHISPER_BEAM_SIZE,
        vad_filter=True,
    )
    pieces = [seg.text for seg in segments]
    text = "".join(pieces).strip()
    return text, info.language or lang, float(info.duration or 0.0)


async def transcribe(upload: UploadFile, language: str) -> Tuple[str, str, float]:
    """Returns (transcript, language, duration_seconds)."""
    total_started = time.perf_counter()
    filename = upload.filename or "audio"

    save_started = time.perf_counter()
    path = await _save_temp(upload)
    save_seconds = time.perf_counter() - save_started
    logger.info("Audio saved (%s) in %.2fs", filename, save_seconds)

    try:
        transcribe_started = time.perf_counter()
        text, detected_lang, duration = await asyncio.to_thread(
            _transcribe_file, path, language
        )
        transcribe_seconds = time.perf_counter() - transcribe_started
        total_seconds = time.perf_counter() - total_started
        logger.info(
            "Transcription done: file=%s audio=%.1fs transcribe=%.1fs total=%.1fs chars=%d",
            filename,
            duration,
            transcribe_seconds,
            total_seconds,
            len(text),
        )
        return text, detected_lang, duration
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
