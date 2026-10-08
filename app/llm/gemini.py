import time
from typing import Any
from app.config import settings
from app.llm.base import LLMResult, ToolCallRequest

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiBackend:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.client = None
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini Client: {e}")

    def generate(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResult:
        start_t = time.perf_counter()

        if not self.api_key:
            ms = (time.perf_counter() - start_t) * 1000.0
            return LLMResult(
                text="[API Key Missing] Please set GEMINI_API_KEY in your .env file to enable live Gemini answers.",
                model=self.model,
                ms=ms,
            )

        if not self.client:
            ms = (time.perf_counter() - start_t) * 1000.0
            return LLMResult(
                text="[Gemini Unavailable] Client initialization failed.",
                model=self.model,
                ms=ms,
            )

        try:
            # Build conversation contents for GenAI SDK
            formatted_contents = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant"):
                    formatted_contents.append(
                        {"role": role, "parts": [{"text": content}]}
                    )

            # Build tools config if offered tools exist
            genai_tools = None
            if tools:
                # Function declaration specs for offered tools
                declarations = []
                for t in tools:
                    declarations.append(
                        types.FunctionDeclaration(
                            name=t["name"],
                            description=t.get("description", ""),
                            parameters=t.get("parameters"),
                        )
                    )
                genai_tools = [types.Tool(function_declarations=declarations)]

            config = types.GenerateContentConfig(
                system_instruction=system if system else None,
                tools=genai_tools,
                temperature=0.2,
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=formatted_contents,
                config=config,
            )

            ms = (time.perf_counter() - start_t) * 1000.0
            text_out = response.text if response.text else None
            tool_calls_out = []

            if hasattr(response, "function_calls") and response.function_calls:
                for fc in response.function_calls:
                    tool_calls_out.append(
                        ToolCallRequest(
                            name=fc.name,
                            args=dict(fc.args) if fc.args else {},
                        )
                    )

            return LLMResult(
                text=text_out,
                tool_calls=tool_calls_out,
                model=self.model,
                ms=ms,
            )

        except Exception as e:
            ms = (time.perf_counter() - start_t) * 1000.0
            return LLMResult(
                text=f"[Gemini Error] Call failed: {e}",
                model=self.model,
                ms=ms,
            )
