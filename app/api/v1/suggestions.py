from fastapi import APIRouter, HTTPException

from app.schemas.suggestions import (
    SuggestionItem,
    SuggestionsData,
    SuggestionsRequest,
    SuggestionsResponse,
)
from app.services import llm_service

router = APIRouter()


@router.post("/suggestions", response_model=SuggestionsResponse)
async def extract_suggestions(body: SuggestionsRequest):
    try:
        parsed = await llm_service.extract_suggestions(
            agreements=body.agreements,
            project_members=[m.model_dump() for m in body.project_members],
            language=body.language,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Suggestion extraction failed: {exc}")

    items = []
    for s in parsed.get("suggestions", []) or []:
        try:
            items.append(SuggestionItem(**s))
        except Exception:  # noqa: BLE001
            continue

    return SuggestionsResponse(data=SuggestionsData(suggestions=items))
