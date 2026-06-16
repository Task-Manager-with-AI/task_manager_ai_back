"""Agent step engine — one turn of an OpenAI-compatible tool-calling loop.

The orchestration loop (executing tools, enforcing permissions) lives in the
Express backend. This service is stateless: given the conversation so far + the
tool catalog, it asks the LLM for the next message, which is either a final
answer or one or more tool calls for the backend to execute.

Provider-driven, mirroring llm_service.py (DeepSeek via the OpenAI-compatible
API; Ollama as the local fallback).
"""
import json
import logging
from typing import Any, Dict, List

from fastapi import HTTPException

from app.core.config import settings
from app.schemas.agent import AgentMessage, AgentStepData, ToolCall

logger = logging.getLogger(__name__)


def run_step(
    messages: List[AgentMessage],
    tools: List[Dict[str, Any]],
    temperature: float = 0.2,
) -> AgentStepData:
    if settings.AI_PROVIDER == "deepseek":
        return _step_deepseek(messages, tools, temperature)
    return _step_ollama(messages, tools, temperature)


def _to_openai_messages(messages: List[AgentMessage]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in messages:
        entry: Dict[str, Any] = {"role": m.role, "content": m.content or ""}
        if m.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in m.tool_calls
            ]
            # Assistant messages that only request tools may have empty content.
            entry["content"] = m.content or ""
        if m.tool_call_id:
            entry["tool_call_id"] = m.tool_call_id
        out.append(entry)
    return out


def _parse_tool_calls(raw_tool_calls: Any) -> List[ToolCall]:
    parsed: List[ToolCall] = []
    for tc in raw_tool_calls or []:
        fn = getattr(tc, "function", None)
        name = getattr(fn, "name", None) if fn else None
        raw_args = getattr(fn, "arguments", None) if fn else None
        if not name:
            continue
        try:
            args = json.loads(raw_args) if raw_args else {}
        except (json.JSONDecodeError, TypeError):
            args = {}
        parsed.append(ToolCall(id=getattr(tc, "id", name), name=name, arguments=args))
    return parsed


def _step_deepseek(
    messages: List[AgentMessage], tools: List[Dict[str, Any]], temperature: float
) -> AgentStepData:
    if not settings.DEEPSEEK_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="DEEPSEEK_API_KEY is not configured. Set AI_PROVIDER=local to use Ollama.",
        )
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )
    kwargs: Dict[str, Any] = {
        "model": settings.DEEPSEEK_LLM_MODEL,
        "messages": _to_openai_messages(messages),
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    completion = client.chat.completions.create(**kwargs)
    choice = completion.choices[0]
    msg = choice.message
    tool_calls = _parse_tool_calls(getattr(msg, "tool_calls", None))

    return AgentStepData(
        message=AgentMessage(
            role="assistant",
            content=msg.content or "",
            tool_calls=tool_calls or None,
        ),
        finish_reason=choice.finish_reason or "stop",
    )


def _step_ollama(
    messages: List[AgentMessage], tools: List[Dict[str, Any]], temperature: float
) -> AgentStepData:
    try:
        import ollama
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="ollama package not installed. Run: pip install ollama",
        ) from exc

    client = ollama.Client(host=settings.OLLAMA_HOST)
    response = client.chat(
        model=settings.OLLAMA_LLM_MODEL,
        messages=_to_openai_messages(messages),
        tools=tools or None,
        options={"temperature": temperature},
    )
    msg = response.get("message", {})
    tool_calls: List[ToolCall] = []
    for tc in msg.get("tool_calls", []) or []:
        fn = tc.get("function", {})
        name = fn.get("name")
        if not name:
            continue
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        tool_calls.append(ToolCall(id=tc.get("id", name), name=name, arguments=args))

    return AgentStepData(
        message=AgentMessage(
            role="assistant",
            content=msg.get("content", "") or "",
            tool_calls=tool_calls or None,
        ),
        finish_reason="tool_calls" if tool_calls else "stop",
    )
