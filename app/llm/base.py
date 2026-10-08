from typing import Any, Protocol
from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    id: str | None = None
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class LLMResult(BaseModel):
    text: str | None = None
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    model: str = ""
    ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMBackend(Protocol):
    def generate(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResult:
        ...
