import hashlib
import time
from typing import Optional
from app.config import settings

try:
    from transformers import pipeline as hf_pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class InjectionClassifier:
    def __init__(self, model_id: Optional[str] = None, device: Optional[str] = None):
        self.model_id = model_id or settings.CLASSIFIER_MODEL
        self.device = device or settings.CLASSIFIER_DEVICE
        self._pipe = None
        self._cache: dict[str, float] = {}

    def _ensure_loaded(self) -> bool:
        if self._pipe is not None:
            return True
        if not TRANSFORMERS_AVAILABLE:
            return False

        try:
            device_id = -1 if self.device == "cpu" else 0
            self._pipe = hf_pipeline(
                "text-classification",
                model=self.model_id,
                tokenizer=self.model_id,
                device=device_id,
                truncation=True,
                max_length=512,
            )
            return True
        except Exception as e:
            print(f"Failed to load Hugging Face classifier '{self.model_id}': {e}")
            return False

    def predict_single(self, text: str) -> float:
        if not text or not text.strip():
            return 0.0

        # SHA-256 Caching
        cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self._ensure_loaded():
            return 0.0

        try:
            results = self._pipe(text)
            if results and isinstance(results, list):
                res = results[0]
                label = str(res.get("label", "")).lower()
                score = float(res.get("score", 0.0))
                # ProtectAI labels: 'INJECTION' or 'SAFE' / 'LABEL_1'
                if "injection" in label or label in ("label_1", "unsafe"):
                    prob = score
                else:
                    prob = 1.0 - score if score > 0.5 else 0.0
                
                self._cache[cache_key] = prob
                return prob
        except Exception as e:
            print(f"Classifier prediction error: {e}")

        return 0.0

    def predict_batch(self, texts: list[str]) -> list[float]:
        if not texts:
            return []

        results_list = [0.0] * len(texts)
        to_fetch_indices = []
        to_fetch_texts = []

        # Check SHA-256 Cache first
        for i, t in enumerate(texts):
            if not t or not t.strip():
                results_list[i] = 0.0
                continue

            cache_key = hashlib.sha256(t.encode("utf-8")).hexdigest()
            if cache_key in self._cache:
                results_list[i] = self._cache[cache_key]
            else:
                to_fetch_indices.append(i)
                to_fetch_texts.append(t)

        if not to_fetch_texts:
            return results_list

        if not self._ensure_loaded():
            return results_list

        try:
            batch_results = self._pipe(to_fetch_texts)
            for idx, res in zip(to_fetch_indices, batch_results):
                label = str(res.get("label", "")).lower()
                score = float(res.get("score", 0.0))
                if "injection" in label or label in ("label_1", "unsafe"):
                    prob = score
                else:
                    prob = 1.0 - score if score > 0.5 else 0.0

                cache_key = hashlib.sha256(texts[idx].encode("utf-8")).hexdigest()
                self._cache[cache_key] = prob
                results_list[idx] = prob
        except Exception as e:
            print(f"Classifier batch prediction error: {e}")

        return results_list

    def warmup(self):
        print(f"Warming up classifier '{self.model_id}'...")
        start_t = time.perf_counter()
        self.predict_single("Warm-up dummy text for prompt injection classifier.")
        dur = (time.perf_counter() - start_t) * 1000.0
        print(f"Classifier warmed up in {dur:.1f}ms.")


classifier = InjectionClassifier()
