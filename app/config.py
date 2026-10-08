import os
from pathlib import Path
from typing import Any
import yaml
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_BACKEND: str = os.getenv("LLM_BACKEND", "gemini")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    CLASSIFIER_MODEL: str = os.getenv(
        "CLASSIFIER_MODEL", "protectai/deberta-v3-base-prompt-injection-v2"
    )
    CLASSIFIER_DEVICE: str = os.getenv("CLASSIFIER_DEVICE", "cpu")
    JUDGE_ENABLED: bool = os.getenv("JUDGE_ENABLED", "true").lower() == "true"
    JUDGE_TIMEOUT_S: float = float(os.getenv("JUDGE_TIMEOUT_S", "3"))
    LLM_TIMEOUT_S: float = float(os.getenv("LLM_TIMEOUT_S", "30"))
    MAX_AGENT_TURNS: int = int(os.getenv("MAX_AGENT_TURNS", "4"))
    MAX_MESSAGE_CHARS: int = int(os.getenv("MAX_MESSAGE_CHARS", "8000"))
    MAX_FILE_MB: float = float(os.getenv("MAX_FILE_MB", "5"))
    MAX_CHUNKS_PER_DOC: int = int(os.getenv("MAX_CHUNKS_PER_DOC", "200"))
    HIDDEN_TEXT_BONUS: float = float(os.getenv("HIDDEN_TEXT_BONUS", "0.30"))
    DOC_DROP_RATIO: float = float(os.getenv("DOC_DROP_RATIO", "0.5"))
    DB_PATH: str = os.getenv("DB_PATH", "logs/gateway.db")


settings = Settings()


def get_profile_path(profile_id: str) -> Path:
    return BASE_DIR / "config" / "profiles" / f"{profile_id}.yaml"


def load_profile(profile_id: str) -> dict[str, Any]:
    path = get_profile_path(profile_id)
    if not path.exists():
        raise ValueError(f"Unknown profile: {profile_id}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_profiles() -> list[dict[str, str]]:
    profiles_dir = BASE_DIR / "config" / "profiles"
    results = []
    if profiles_dir.exists():
        for p in profiles_dir.glob("*.yaml"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    results.append(
                        {
                            "id": data.get("id", p.stem),
                            "display_name": data.get(
                                "display_name", p.stem.title()
                            ),
                        }
                    )
            except Exception:
                pass
    return results


def load_injection_rules() -> list[dict[str, Any]]:
    rules_path = BASE_DIR / "config" / "rules" / "injection_patterns.yaml"
    if not rules_path.exists():
        return []
    with open(rules_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def load_pii_rules() -> list[dict[str, Any]]:
    pii_path = BASE_DIR / "config" / "rules" / "pii_patterns.yaml"
    if not pii_path.exists():
        return []
    with open(pii_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []
