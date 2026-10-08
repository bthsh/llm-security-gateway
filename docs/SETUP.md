# SETUP

## Requirements
- Python 3.11+
- Git
- Internet for the first install and for Gemini
- Laptop: i7 HX, RTX 4070 laptop GPU, 16 GB RAM (classifier and Presidio run on CPU)

## Packages (`requirements.txt`)
Verify each name on PyPI, then pin versions once everything works:

```
fastapi
uvicorn[standard]
python-multipart        # file uploads in FastAPI
pydantic
python-dotenv
pyyaml
httpx
pypdf
pdfminer.six
beautifulsoup4
transformers
torch                   # CPU build is enough
presidio-analyzer
presidio-anonymizer
spacy
google-genai            # official Google Gen AI SDK; verify current usage in Google's docs
pytest
```

## Install

```bash
git clone <repo-url> && cd llm-security-gateway
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm      # small model; configure Presidio to use it
cp .env.example .env                          # then add GEMINI_API_KEY and model names
python scripts/download_models.py             # downloads the classifier for offline use
python scripts/make_samples.py                # creates fake sample PDF/HTML/EML files
```

Get the Gemini key from Google AI Studio. Check your free-tier limits for your chosen model in the AI Studio console.

## Run

```bash
uvicorn app.main:app --reload --port 8000
# open http://localhost:8000
```

Tests and evaluation:
```bash
pytest
python tests/run_eval.py --mode scan     # detection only, no Gemini calls
python tests/run_eval.py --mode full     # full pipeline, uses Gemini quota
```

## Before the event (offline preparation)
- [ ] Classifier downloaded (`scripts/download_models.py`); gated models: licence accepted in advance
- [ ] spaCy model installed
- [ ] Gemini key works; free-tier limits checked
- [ ] Sample files generated
- [ ] App starts with wifi off (Gemini calls will fail, everything else must load)
- [ ] Optional Ollama fallback pulled and tested
- [ ] Backup screen recording of the demo

## Common problems

| Problem | Fix |
|---|---|
| `429` from Gemini | Rate limit: wait, reduce eval size, check limits in AI Studio |
| Classifier download fails | Check model id and licence acceptance; download on good wifi |
| Presidio asks for `en_core_web_lg` | Configure it to use `en_core_web_sm` |
| File upload error | `python-multipart` missing |
| Slow first request | Models not warmed up; startup warm-up call missing |
| Port in use | Use `--port 8001` |
