import os
import tempfile
from typing import Tuple

import aiofiles
from fastapi import UploadFile, HTTPException

from app.core.config import settings

_local_model = None


async def _save_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1] or ".webm"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    async with aiofiles.open(path, "wb") as f:
        while chunk := await upload.read(1024 * 1024):
            await f.write(chunk)
    return path


async def transcribe(upload: UploadFile, language: str) -> Tuple[str, str, float]:
    """Returns (transcript, language, duration_seconds).

    DeepSeek has no audio API — both ``deepseek`` and ``local`` use faster-whisper.
    """
    return await _transcribe_local(upload, language)


async def _transcribe_local(upload: UploadFile, language: str) -> Tuple[str, str, float]:
    global _local_model
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="faster-whisper is not installed. Run: pip install faster-whisper",
        ) from exc

    if _local_model is None:
        _local_model = WhisperModel(
            settings.LOCAL_WHISPER_MODEL,
            device=settings.LOCAL_WHISPER_DEVICE,
            compute_type=settings.LOCAL_WHISPER_COMPUTE_TYPE,
        )

    path = await _save_temp(upload)
    try:
        segments, info = _local_model.transcribe(
            path,
            language=language or settings.DEFAULT_LANGUAGE,
            vad_filter=True,
        )
        pieces = []
        for seg in segments:
            pieces.append(seg.text)
        text = "".join(pieces).strip()
        return text, info.language or language, float(info.duration or 0.0)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
