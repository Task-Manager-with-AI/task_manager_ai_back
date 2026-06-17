"""Embedding generation, provider-driven (mirrors llm_service.py).

EMBEDDING_PROVIDER selects the backend:
  - "openai": OpenAI embeddings API (text-embedding-3-small, 1536 dims).
  - "local":  sentence-transformers on CPU (multilingual).

All callers go through `embed_texts`, which returns one vector per input text.
The vector dimension must match the pgvector column in the backend DB.
"""
import logging
from typing import List

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cached local model (loaded lazily — only when EMBEDDING_PROVIDER=local).
_local_model = None


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts. Empty strings are embedded as zero vectors so the
    output length always matches the input length (1:1)."""
    if not texts:
        return []
    if settings.EMBEDDING_PROVIDER == "openai":
        return _embed_openai(texts)
    return _embed_local(texts)


def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    vectors = embed_texts([text or ""])
    return vectors[0] if vectors else [0.0] * settings.EMBEDDING_DIM


def preload_embedding_model() -> None:
    """Load the local sentence-transformers model into memory (no-op for openai)."""
    if settings.EMBEDDING_PROVIDER != "local":
        return
    embed_texts(["warmup"])
    logger.info("Local embedding model ready (%s)", settings.LOCAL_EMBEDDING_MODEL)


def _embed_openai(texts: List[str]) -> List[List[float]]:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured. Set EMBEDDING_PROVIDER=local to embed on-device.",
        )
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    out: List[List[float]] = []
    batch_size = max(1, settings.EMBEDDING_BATCH_SIZE)
    # OpenAI rejects empty strings; substitute a single space and keep order.
    safe = [t if (t and t.strip()) else " " for t in texts]
    for i in range(0, len(safe), batch_size):
        chunk = safe[i : i + batch_size]
        resp = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=chunk,
            dimensions=settings.EMBEDDING_DIM,
        )
        out.extend([item.embedding for item in resp.data])
    return out


def _embed_local(texts: List[str]) -> List[List[float]]:
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail="sentence-transformers not installed. Run: pip install sentence-transformers",
            ) from exc
        logger.info("Loading local embedding model %s", settings.LOCAL_EMBEDDING_MODEL)
        _local_model = SentenceTransformer(settings.LOCAL_EMBEDDING_MODEL)

    safe = [t if (t and t.strip()) else " " for t in texts]
    vectors = _local_model.encode(
        safe,
        batch_size=max(1, settings.EMBEDDING_BATCH_SIZE),
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return [vec.tolist() for vec in vectors]
