# FILE STRUCTURE

Put code exactly here. Do not create new top-level folders without asking.

```
llm-security-gateway/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example                 # GEMINI_API_KEY= and settings, no real values
├── .gitignore                   # .env, .venv, logs/, data/runtime/, __pycache__/
│
├── docs/                        # all planning docs (this folder)
│
├── app/
│   ├── main.py                  # FastAPI app: routes, serves ui/, startup (load models once)
│   ├── config.py                # settings from .env, loads profiles and rules
│   ├── models.py                # Pydantic models: Segment, Chunk, Finding, StageResult,
│   │                            #   ToolCall, RequestContext, ChatResponse, ...
│   ├── pipeline.py              # runs Guard A, assistant loop, Guard B, audit; early exit; fail closed
│   ├── sessions.py              # in-memory sessions: taint flag, layers, pending approvals, outbox
│   │
│   ├── guard_a/
│   │   ├── normalize.py         # step 1
│   │   ├── extract.py           # step 2: extract_pdf, extract_html, extract_email, extract_text
│   │   ├── provenance.py        # step 3
│   │   ├── chunking.py          # split segments into chunks
│   │   ├── rules.py             # rule matching (patterns from config/rules/)
│   │   ├── classifier.py        # Hugging Face classifier wrapper (loaded once)
│   │   ├── judge.py             # optional LLM judge for borderline chunks
│   │   ├── detect.py            # step 4: combines rules, classifier, hidden bonus, judge
│   │   ├── decide.py            # step 5
│   │   ├── spotlight.py         # step 6
│   │   └── canary_tools.py      # step 7: canary + tool scoping
│   │
│   ├── llm/
│   │   ├── base.py              # LLMBackend interface: generate(system, messages, tools) -> LLMResult
│   │   ├── gemini.py            # Gemini backend
│   │   └── ollama.py            # optional fallback backend
│   │
│   ├── assistant/
│   │   ├── loop.py              # tool-calling loop (max turns), calls policy before any tool runs
│   │   ├── prompts.py           # builds the system prompt from profile + canary + spotlight rule
│   │   └── tools.py             # lookup_record, read_document, send_email (Outbox)
│   │
│   ├── guard_b/
│   │   ├── policy.py            # step 8
│   │   └── output_firewall.py   # step 9
│   │
│   ├── audit/
│   │   └── log.py               # step 10: SQLite writes and reads
│   │
│   └── metrics.py               # reads evaluation results for the scoreboard
│
├── config/
│   ├── profiles/
│   │   ├── customer_support.yaml
│   │   └── finance_hr.yaml
│   └── rules/
│       ├── injection_patterns.yaml
│       └── pii_patterns.yaml
│
├── data/
│   ├── customer_support/
│   │   ├── records.json         # fake customers and orders
│   │   └── documents/           # fake documents read_document may open
│   ├── finance_hr/
│   │   ├── records.json         # fake employees
│   │   └── documents/
│   ├── samples/                 # demo files: poisoned email, hidden-text PDF, hidden-div page, clean files
│   └── runtime/                 # outbox and temp files (gitignored)
│
├── ui/
│   ├── index.html               # the console
│   ├── styles.css
│   └── app.js                   # calls /api/*, renders results; no hard-coded data
│
├── tests/
│   ├── unit/                    # one test file per module: test_normalize.py, test_extract.py, ...
│   ├── integration/             # pipeline tests with a scripted fake backend (tests only)
│   ├── data/
│   │   ├── attacks.jsonl
│   │   └── normal.jsonl
│   └── run_eval.py              # evaluation script, writes results to SQLite
│
├── scripts/
│   ├── download_models.py       # pre-download classifier and spaCy model for offline use
│   └── make_samples.py          # generates the sample PDF/HTML/EML files with fake data
│
└── logs/
    └── gateway.db               # SQLite (gitignored, created at runtime)
```

## Placement rules

- One pipeline step per file. A step file exposes one main function: `run(ctx: RequestContext) -> StageResult`.
- Shared data shapes only in `app/models.py`. Do not define the same shape twice.
- Settings only in `app/config.py`. No `os.getenv` elsewhere.
- Patterns and thresholds in `config/`, never hard-coded in Python.
- Fake test doubles (such as a scripted LLM backend) live **only** under `tests/`. The running app never uses them.
- The UI only calls `/api/*`. It never contains sample results.
- Runtime files (`logs/`, `data/runtime/`) are created on startup if missing and are gitignored.
