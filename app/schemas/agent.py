from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class AgentMessage(BaseModel):
    """OpenAI-compatible chat message. `tool_calls` is set on assistant turns
    that request tools; `tool_call_id` links a tool result back to its call."""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None


class AgentStepRequest(BaseModel):
    messages: List[AgentMessage] = Field(default_factory=list)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.2


class AgentStepData(BaseModel):
    message: AgentMessage
    finish_reason: str = "stop"


class AgentStepResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: AgentStepData
