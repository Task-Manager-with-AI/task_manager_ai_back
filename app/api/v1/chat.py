from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatSummaryData, ChatSummaryRequest, ChatSummaryResponse
from app.services import llm_service

router = APIRouter(tags=["chat"])


@router.post(
    "/chat-summary",
    response_model=ChatSummaryResponse,
    summary="Summarize recent chat messages (¿Qué me perdí?)",
)
async def chat_summary(body: ChatSummaryRequest):
    """
    Summarize recent / unread chat messages into 3-5 bullets so a user
    returning to a busy conversation can catch up quickly.
    """
    try:
        parsed = await llm_service.summarize_chat(
            transcript=body.transcript,
            language=body.language,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Chat summary failed: {exc}")

    return ChatSummaryResponse(data=ChatSummaryData(summary=parsed.get("summary", []) or []))
