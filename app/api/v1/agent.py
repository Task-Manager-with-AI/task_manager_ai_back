import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas.agent import AgentStepRequest, AgentStepResponse
from app.services import agent_service

router = APIRouter(tags=["agent"])


@router.post(
    "/agent/step",
    response_model=AgentStepResponse,
    summary="Run one tool-calling step of the RAG agent (stateless)",
)
async def agent_step(body: AgentStepRequest):
    """One LLM turn: given the conversation + tool catalog, return the next
    assistant message (a final answer or tool calls). The Express backend owns
    the loop and executes tools with the user's permissions."""
    try:
        data = await asyncio.to_thread(
            agent_service.run_step, body.messages, body.tools, body.temperature
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Agent step failed: {exc}")

    return AgentStepResponse(data=data)
