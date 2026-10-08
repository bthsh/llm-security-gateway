import time
from typing import Any
import httpx
from app.config import settings
from app.llm.base import LLMResult, ToolCallRequest


class OllamaBackend:
    def __init__(self, url: str | None = None, model: str | None = None):
        self.url = (url or settings.OLLAMA_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL

    def generate(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResult:
        start_t = time.perf_counter()

        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=settings.LLM_TIMEOUT_S) as client:
                resp = client.post(f"{self.url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()

            ms = (time.perf_counter() - start_t) * 1000.0
            content = data.get("message", {}).get("content", "")
            return LLMResult(
                text=content,
                tool_calls=[],
                model=self.model,
                ms=ms,
            )
        except Exception as e:
            ms = (time.perf_counter() - start_t) * 1000.0
            return LLMResult(
                text=f"[Ollama Error] Could not connect to Ollama at {self.url}: {e}",
                model=self.model,
                ms=ms,
            )
