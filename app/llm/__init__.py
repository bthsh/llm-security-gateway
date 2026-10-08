from app.config import settings
from app.llm.base import LLMBackend
from app.llm.gemini import GeminiBackend
from app.llm.groq_backend import GroqBackend
from app.llm.ollama import OllamaBackend


def get_llm_backend() -> LLMBackend:
    backend_name = (settings.LLM_BACKEND or "gemini").lower()
    if backend_name == "groq":
        return GroqBackend()
    elif backend_name == "ollama":
        return OllamaBackend()
    else:
        return GeminiBackend()
