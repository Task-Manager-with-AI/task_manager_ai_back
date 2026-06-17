import asyncio

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.embeddings import EmbeddingsData, EmbeddingsRequest, EmbeddingsResponse
from app.services import embedding_service

router = APIRouter(tags=["embeddings"])


@router.post(
    "/embeddings",
    response_model=EmbeddingsResponse,
    summary="Generate embeddings for a batch of texts (RAG indexing + queries)",
)
async def create_embeddings(body: EmbeddingsRequest):
    try:
        # Embedding calls are blocking (HTTP or CPU); run off the event loop.
        vectors = await asyncio.to_thread(embedding_service.embed_texts, body.texts)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}")

    # Report the actual produced dimension (the local model may differ from
    # EMBEDDING_DIM, which only drives the OpenAI `dimensions` param).
    actual_dim = len(vectors[0]) if vectors and vectors[0] else settings.EMBEDDING_DIM

    return EmbeddingsResponse(
        data=EmbeddingsData(
            vectors=vectors,
            model=settings.EMBEDDING_MODEL
            if settings.EMBEDDING_PROVIDER == "openai"
            else settings.LOCAL_EMBEDDING_MODEL,
            dim=actual_dim,
        )
    )
