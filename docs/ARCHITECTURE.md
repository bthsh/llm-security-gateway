# ARCHITECTURE

## System view

```
 Clients                        GATEWAY (FastAPI)                         LLM
┌────────────┐     ┌──────────────────────────────────────────┐     ┌──────────┐
│ Console UI │     │ GUARD A  1 normalize  2 extract          │     │ Gemini   │
│ curl / any │────▶│          3 provenance 4 detect (+judge)  │────▶│ (Ollama  │
│ app        │     │          5 decide     6 spotlight        │     │ optional)│
│ PDF / HTML │     │          7 canary + tool scoping         │◀────│          │
│ / EML      │◀────│ GUARD B  8 policy     9 output firewall  │     └──────────┘
└────────────┘     │ 10 audit log (records every step)        │
                   └───────┬───────────────┬──────────────────┘
                           │               │
                  ┌────────▼─────┐  ┌──────▼─────────┐
                  │ config/      │  │ logs/gateway.db│
                  │ profiles,    │  │ (SQLite)       │
                  │ rules (YAML) │  └────────────────┘
                  └──────────────┘
```

The gateway does not know which company it protects. Company specifics live in `config/profiles/*.yaml`.

## Request flow (console chat, `POST /api/chat`)

1. **Receive** message, attachments, session id, profile id.
2. **Guard A** on every incoming segment:
   1. Normalize
   2. Extract (attachments become `document`, `web` or `email` segments)
   3. Tag provenance (`user` trusted; attachments untrusted)
   4. Detect per chunk (rules, classifier, hidden-text bonus; judge only for borderline)
   5. Decide per chunk and per request
      - User message blocked → **early exit**: steps 6-9 `SKIPPED`, log, return `BLOCKED`
      - Untrusted chunks removed → continue with the cleaned text
   6. Spotlight untrusted text
   7. Plant canary in the system prompt; mark session tainted if untrusted content is present; remove risky tools from the offered list if tainted
3. **Assistant loop** (max `MAX_AGENT_TURNS`):
   - Call the LLM with system prompt, conversation and offered tools
   - If the LLM returns tool calls → **step 8 policy engine** checks each one
     - Allowed → execute the tool → the **tool result is untrusted** and goes through steps 1-6 before being returned to the LLM
     - Blocked → the LLM is told "action blocked: <reason>"
     - Needs approval → stop the loop, return `NEEDS_APPROVAL`
   - If the LLM returns text → leave the loop
4. **Guard B step 9** on the final reply: canary check, link/image stripping, decode-then-scan, redaction
5. **Step 10** writes all step results and timings to SQLite
6. **Return** decision, reply, trace, before/after, tool calls, Outbox, redactions, timings

## Why Guard B cannot move into Guard A

Steps 8 and 9 check things the AI creates: tool calls and the reply. They do not exist before the LLM answers. The only part that could move forward (tool scoping) has already moved into step 7.

## Sessions and taint

- Each console tab has a `session_id`.
- A session becomes **tainted** when untrusted content enters (attachment or tool result) or a borderline user message is not resolved.
- Taint lasts until `POST /api/reset`.
- Tool scoping is recalculated **every assistant turn**.

## Layers (demo switches)

Stored per session. Can be turned off for demonstration only:
`classifier`, `judge`, `tool_scoping`, `policy_engine`, `output_firewall`.
Normalize, extract, provenance, decide, spotlight, canary and audit cannot be turned off. The console shows a warning banner while any layer is off.

## Fail closed

| Failure | Behaviour |
|---|---|
| Classifier error | Score falls back to rules only, step marked `ERROR`, session tainted |
| Judge error or timeout | Untrusted borderline chunk removed; user borderline message → session tainted |
| Policy engine error | Tool call blocked |
| Output firewall error | Reply withheld |
| LLM error or timeout | Return an error message; nothing executed |
| Extractor error | File content dropped and reported; request continues without it |

## OpenAI-style endpoint (`POST /v1/chat/completions`)

Text only. Runs Guard A on the messages (`system` and `user` trusted, any other role untrusted), calls the backend, runs step 9 on the reply, logs. No tools. Purpose: show that any client can use the gateway by changing its base URL.

## Tech stack

| Part | Choice | Why | Not chosen |
|---|---|---|---|
| Language | Python 3.11+ | Best ML and security libraries | Node/Java/Go: weaker ML support |
| Server | FastAPI + Uvicorn | Async, fast, built-in validation | Flask (no validation), Django (too heavy) |
| Models/contracts | Pydantic v2 | Same checked structure for every step | Plain dicts (bugs slip through) |
| PDF | pypdf + pdfminer.six | Text, metadata, annotations; font size and colour | PyMuPDF (AGPL licence), OCR (out of scope) |
| HTML | BeautifulSoup (`html.parser`) | Finds comments and hidden elements | Headless browser (too heavy for 24 h) |
| Email | Python `email` module | Built in | Third-party parsers (not needed) |
| Classifier | Hugging Face `transformers` + a pretrained prompt-injection model | Local, fast, generalizes to rewording | Training our own; paid cloud APIs |
| LLM + judge | Gemini via the official Google Gen AI SDK | Strong tool calling, free tier | Paid APIs; weak local models |
| Fallback | Ollama (optional) | Offline backup | - |
| PII | Regex + Presidio (spaCy) | Structured patterns + names/addresses | Cloud DLP (data leaves the machine) |
| Config | YAML | Readable, comments | JSON, database |
| Storage | SQLite | Zero setup | PostgreSQL (needs a server) |
| Console | HTML + CSS + JavaScript | Matches the designed look, no build step | Streamlit (limited look), React (extra toolchain) |
| Tests | pytest | Standard | Manual testing |
