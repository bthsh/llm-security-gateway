# CONFIG

## Environment variables (`.env`, never committed)

| Name | Example | Notes |
|---|---|---|
| `GEMINI_API_KEY` | (secret) | Required. From Google AI Studio. Never log it. |
| `LLM_BACKEND` | `gemini` | `gemini` or `ollama` |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Read from `.env` only (never hard-coded); user verifies free tier availability before setting |
| `OLLAMA_URL` | `http://localhost:11434` | Optional fallback |
| `OLLAMA_MODEL` | (set if used) | A local 7B-8B instruct model with tool support |
| `CLASSIFIER_MODEL` | `protectai/deberta-v3-base-prompt-injection-v2` | Primary Hugging Face classifier candidate (English-focused) |
| `CLASSIFIER_DEVICE` | `cpu` | Keep CPU so the GPU stays free |
| `JUDGE_ENABLED` | `true` | Optional judge |
| `JUDGE_TIMEOUT_S` | `3` | |
| `LLM_TIMEOUT_S` | `30` | |
| `MAX_AGENT_TURNS` | `4` | |
| `MAX_MESSAGE_CHARS` | `8000` | |
| `MAX_FILE_MB` | `5` | |
| `MAX_CHUNKS_PER_DOC` | `200` | |
| `HIDDEN_TEXT_BONUS` | `0.30` | |
| `DOC_DROP_RATIO` | `0.5` | |
| `DB_PATH` | `logs/gateway.db` | |

`.env.example` lists every name with empty or safe values.

First candidate classifier: ProtectAI's DeBERTa prompt-injection classifier v2 (`protectai/deberta-v3-base-prompt-injection-v2`). Note: it is English-focused. Alternative: Meta's Prompt Guard 2 (gated: accept licence in advance).

## Profile file (`config/profiles/<id>.yaml`)

```yaml
id: customer_support
display_name: "Customer Support"
system_prompt: |
  You are a customer support assistant for Example Foods (a fictional company).
  Answer questions about orders using the tools. Be brief and polite.

data:
  records_file: data/customer_support/records.json
  documents_dir: data/customer_support/documents

tools:
  lookup_record:
    risky: false
    record_id_pattern: "^ORD-[0-9]{4}$"
  read_document:
    risky: false
  send_email:
    risky: true
    allowed_email_domains: ["examplefoods.example"]

on_taint: block            # block | approve  (risky tools when session is tainted)

intents:                   # goal-consistency keywords per tool
  lookup_record: ["order", "record", "status", "track", "delivery", "customer"]
  read_document: ["document", "file", "pdf", "email", "page", "summarize", "summary", "read", "policy"]
  send_email:    ["send", "email", "reply", "forward", "mail", "notify"]

thresholds:
  user:      {borderline_low: 0.50, block: 0.80}
  untrusted: {borderline_low: 0.40, remove: 0.80}

output:
  allowed_link_domains: ["examplefoods.example"]
  redaction_allowlist: ["support@examplefoods.example"]
  redact_person_names: false
```

`config/profiles/finance_hr.yaml` uses the same keys with different values, for example:
- `system_prompt` for an internal HR assistant of "Example Corp" (fictional)
- `record_id_pattern: "^EMP-[0-9]{4}$"`
- `allowed_email_domains: ["examplecorp.example"]`
- `on_taint: approve`
- stricter thresholds, e.g. `untrusted: {borderline_low: 0.35, remove: 0.75}`
- `redact_person_names: true`

Use only `.example` domains for fake companies (reserved for documentation, never real).

## Rule files

`config/rules/injection_patterns.yaml`
```yaml
- id: instruction_override
  weight: 0.85
  owasp: LLM01
  patterns:
    - "(?i)ignore (all |any )?(previous|prior|above) (instructions|rules)"
    - "(?i)disregard (the )?(system|previous) (prompt|instructions)"
- id: system_prompt_extraction
  weight: 0.80
  owasp: LLM07
  patterns:
    - "(?i)(repeat|print|reveal|show) (everything|all|your) (above|instructions|system prompt)"
- id: fake_delimiter
  weight: 0.75
  owasp: LLM01
  patterns:
    - "(?i)^\\s*#{2,}\\s*(system|assistant)\\s*:"
    - "(?i)</?(system|instructions|document)>"
- id: ai_directed_instruction
  weight: 0.60
  owasp: LLM01
  patterns:
    - "(?i)\\b(ai|assistant|chatbot|model)\\b.{0,20}\\b(must|should|now|please)\\b"
- id: exfiltration_request
  weight: 0.70
  owasp: LLM02
  patterns:
    - "(?i)(send|forward|email|post|upload).{0,40}(customer|record|list|data|password|key)"
- id: role_play_jailbreak
  weight: 0.70
  owasp: LLM01
  patterns:
    - "(?i)(pretend|act as|you are now).{0,40}(no (rules|restrictions|limits)|DAN|unrestricted)"
```
These are starting patterns. Tune them with the test set and watch false positives.

`config/rules/pii_patterns.yaml`: one entry per type (`EMAIL`, `PHONE`, `API_KEY`, `AADHAAR`, `PAN`, `CARD`) with `pattern`, `replacement`, and optional `validator` (e.g. `luhn` for cards).
