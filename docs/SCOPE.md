# SCOPE

What we build, what we do not build, and what to cut if time runs short.

## In scope (MVP)

**Gateway**
- FastAPI service with the 10-step pipeline (Guard A steps 1-7, LLM call, Guard B steps 8-9, step 10 audit log)
- Early exit on block, fail closed on errors
- Session taint tracking and tool scoping (risky tools hidden when tainted)
- Two YAML profiles: `customer_support` and `finance_hr`
- Gemini as the LLM backend
- OpenAI-style endpoint `/v1/chat/completions` (text only, no tools) to prove any client can use the gateway

**Input sources**
- Chat text typed by the user
- Uploaded files: `.pdf`, `.html`/`.htm`, `.eml`, `.txt`
- Tool results returned to the assistant (treated as untrusted)

**Detection**
- Normalization: NFKC, zero-width removal, base64/hex/URL decoding
- Hidden-text extraction: PDF (white/tiny/off-page text, metadata, annotations), HTML (comments, `display:none`, `visibility:hidden`, `hidden` attribute, tiny or off-screen text, `alt` text), email (headers, plain vs HTML parts, attachments)
- Rule patterns in YAML
- One pretrained Hugging Face prompt-injection classifier
- Visible-vs-hidden text difference as a signal

**Protection**
- Allow / clean / block decisions per chunk
- Spotlighting with per-request random tags
- Per-request canary token
- Policy engine: allow-list, argument checks, taint rule, goal-consistency check, human approval
- Output firewall: canary check, removal of external links and images (including reference-style markdown), redaction of personal data and secrets, decode-then-scan

**Demo assistant**
- Gemini tool-calling loop with `lookup_record`, `read_document`, `send_email`
- `send_email` writes to an on-screen Outbox, never to the internet
- Fake records and documents per profile

**Console**
- One-page web UI (HTML, CSS, JavaScript) served by FastAPI, matching the Lovable reference layout (see `UI.md`)

**Proof**
- Attack and normal test sets with fake data
- Evaluation script producing detection, containment, false-positive and latency numbers
- Scoreboard fed only by real evaluation results

## Optional (build only after the MVP works)

- LLM judge for borderline scores (Gemini), switchable in config and in the Layers menu
- Ollama fallback backend

## Out of scope (state these as limits)

- Image-based injection (instructions inside images)
- Scanned PDFs that need OCR
- Hiding done by external CSS files or JavaScript (needs a real browser to render)
- Fine-tuning or training any model
- Dual-LLM / quarantined-LLM architecture
- Tool calling through `/v1/chat/completions`
- Load testing, scaling, multi-user accounts, authentication
- Guaranteed protection against an attacker who studies the system

## Decided NOT to build (do not add these)

- A "gateway OFF" mode or toggle
- Sidebar pages such as "Firewall Rules", "Model Routing", "Incident Forensics"
- SIEM export, "immutable hash", "sandbox verified" labels, forensic JSON export
- Any fake statistic, version tag, session counter or "blocked today" number
- An LLM as the main detector
- Real email sending
- Streamlit or React for the console
- DeepSeek Harness or any other agent framework

## Never cut

1. Indirect injection from documents (PDF, HTML, email)
2. Clean vs block
3. Policy engine
4. Output firewall
5. Pipeline view in the console
6. Measured results

## Cut order if time runs short

1. Ollama fallback
2. LLM judge
3. Email plain-vs-HTML mismatch check
4. Visual polish of the console
5. Second profile (last resort)
