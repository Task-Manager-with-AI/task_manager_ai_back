import asyncio
import logging
import os
import subprocess
import tempfile
import time
from typing import Optional, Tuple

import aiofiles
from fastapi import HTTPException, UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

_local_model = None
_model_load_seconds: float | None = None

_EXT_MIME = {
    ".webm": "audio/webm",
    ".mp3": "audio/mpeg",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".opus": "audio/opus",
}


def uses_local_whisper() -> bool:
    return settings.TRANSCRIPTION_PROVIDER == "local"


def active_whisper_model() -> str:
    provider = settings.TRANSCRIPTION_PROVIDER
    if provider == "openai":
        return settings.OPENAI_WHISPER_MODEL
    if provider == "groq":
        return settings.GROQ_WHISPER_MODEL
    return settings.LOCAL_WHISPER_MODEL


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
    """Load local Whisper into memory (no-op for remote API providers)."""
    if not uses_local_whisper():
        logger.info(
            "Skipping local Whisper preload (TRANSCRIPTION_PROVIDER=%s)",
            settings.TRANSCRIPTION_PROVIDER,
        )
        return
    _load_whisper_model()


def is_model_loaded() -> bool:
    if not uses_local_whisper():
        return True
    return _local_model is not None


def model_load_seconds() -> float | None:
    if not uses_local_whisper():
        return None
    return _model_load_seconds


def _guess_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return _EXT_MIME.get(ext, "application/octet-stream")


def _probe_audio_duration(path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        logger.warning("Could not probe audio duration for %s: %s", path, exc)
    return 0.0


def _transcribe_local(path: str, language: str) -> Tuple[str, str, float]:
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


def _transcribe_remote_api(
    path: str,
    language: str,
    *,
    api_key: Optional[str],
    missing_key_detail: str,
    base_url: Optional[str],
    model: str,
) -> Tuple[str, str, float]:
    if not api_key:
        raise HTTPException(status_code=500, detail=missing_key_detail)

    from openai import OpenAI

    lang = language or settings.DEFAULT_LANGUAGE
    client = OpenAI(api_key=api_key, base_url=base_url)
    filename = os.path.basename(path)
    mime = _guess_mime(path)

    with open(path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=model,
            file=(filename, audio_file, mime),
            language=lang,
            response_format="verbose_json",
        )

    text = (result.text or "").strip()
    detected_lang = result.language or lang
    duration = float(result.duration or 0.0)
    if duration <= 0.0:
        duration = _probe_audio_duration(path)

    return text, detected_lang, duration


def _transcribe_groq(path: str, language: str) -> Tuple[str, str, float]:
    return _transcribe_remote_api(
        path,
        language,
        api_key=settings.GROQ_API_KEY,
        missing_key_detail=(
            "GROQ_API_KEY is not configured. "
            "Get a key at https://console.groq.com/keys or set "
            "TRANSCRIPTION_PROVIDER=local to use faster-whisper."
        ),
        base_url=settings.GROQ_BASE_URL,
        model=settings.GROQ_WHISPER_MODEL,
    )


def _transcribe_openai(path: str, language: str) -> Tuple[str, str, float]:
    return _transcribe_remote_api(
        path,
        language,
        api_key=settings.OPENAI_API_KEY,
        missing_key_detail=(
            "OPENAI_API_KEY is not configured. "
            "Set TRANSCRIPTION_PROVIDER=groq or local for alternatives."
        ),
        base_url=None,
        model=settings.OPENAI_WHISPER_MODEL,
    )


def _transcribe_file(path: str, language: str) -> Tuple[str, str, float]:
    provider = settings.TRANSCRIPTION_PROVIDER
    if provider == "local":
        return _transcribe_local(path, language)
    if provider == "groq":
        return _transcribe_groq(path, language)
    return _transcribe_openai(path, language)


async def _save_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1] or ".webm"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    async with aiofiles.open(path, "wb") as f:
        while chunk := await upload.read(1024 * 1024):
            await f.write(chunk)
    return path


async def transcribe(upload: UploadFile, language: str) -> Tuple[str, str, float]:
    """Returns (transcript, language, duration_seconds)."""
    total_started = time.perf_counter()
    filename = upload.filename or "audio"
    provider = settings.TRANSCRIPTION_PROVIDER

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
            "Transcription done (%s): file=%s audio=%.1fs transcribe=%.1fs total=%.1fs chars=%d",
            provider,
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
