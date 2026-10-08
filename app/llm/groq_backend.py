import json
import time
from typing import Any
from openai import OpenAI

from app.config import settings
from app.llm.base import LLMBackend, LLMResult, ToolCallRequest


def _normalize_json_schema(obj: Any) -> Any:
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            if k == "type" and isinstance(v, str):
                new_dict[k] = v.lower()
            else:
                new_dict[k] = _normalize_json_schema(v)
        return new_dict
    elif isinstance(obj, list):
        return [_normalize_json_schema(item) for item in obj]
    return obj


class GroqBackend(LLMBackend):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.base_url = base_url
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "missing_key",
            timeout=settings.LLM_TIMEOUT_S,
        )

    def generate(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResult:
        start_t = time.perf_counter()
        try:
            chat_messages = []
            if system:
                chat_messages.append({"role": "system", "content": system})

            for m in messages:
                chat_messages.append(
                    {"role": m.get("role", "user"), "content": m.get("content", "")}
                )

            openai_tools = None
            if tools:
                openai_tools = []
                for t in tools:
                    raw_params = t.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    )
                    norm_params = _normalize_json_schema(raw_params)
                    openai_tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": t["name"],
                                "description": t.get("description", ""),
                                "parameters": norm_params,
                            },
                        }
                    )

            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": chat_messages,
            }
            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)
            ms = (time.perf_counter() - start_t) * 1000.0

            choice = response.choices[0]
            msg = choice.message

            tool_calls_req = []
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    args_raw = tc.function.arguments or "{}"
                    try:
                        args = json.loads(args_raw)
                    except Exception:
                        args = {}
                    tool_calls_req.append(
                        ToolCallRequest(id=tc.id, name=fn_name, args=args)
                    )

            text_content = msg.content

            return LLMResult(
                text=text_content,
                tool_calls=tool_calls_req,
                model=self.model,
                ms=ms,
            )

        except Exception as e:
            ms = (time.perf_counter() - start_t) * 1000.0
            return LLMResult(
                text=f"[Groq Error] Call failed: {e}",
                tool_calls=[],
                model=self.model,
                ms=ms,
            )
