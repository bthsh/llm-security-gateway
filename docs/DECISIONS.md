# DECISIONS

These are final. Do not reopen them without the user's approval.

| ID | Decision | Why |
|---|---|---|
| D-01 | Build a **general, model-agnostic gateway**, not a company-specific chatbot | CB-01 asks for "a gateway that sits between users, data sources and an LLM app". Company rules go in YAML profiles. |
| D-02 | **Gemini API (`gemini-3.8-flash`)** is the LLM behind the gateway | Strong instruction-following and tool calling, free tier, no load on the laptop |
| D-03 | **Ollama is an optional fallback**, selected by one setting | Protects the demo if wifi or Gemini fails. Not required for the MVP. |
| D-04 | **No "gateway OFF" mode** | The team chose not to show an unprotected run. Attacks are shown through the hidden text found and the blocked actions. |
| D-05 | **Ten steps: Guard A = steps 1-7, Guard B = steps 8-9, step 10 logs both** | Clear story: check what goes in, check what comes out |
| D-06 | **Tool scoping moved into Guard A (step 7)** | A tricked AI cannot call a tool it was never offered. Stronger than blocking afterwards, costs almost nothing. |
| D-07 | **Guard B is kept** | Guard A can miss reworded attacks, and leaks only exist in the reply (EchoLeak shows this). Guard B costs milliseconds and does not run when Guard A blocks. |
| D-08 | **Early exit**: a block in Guard A stops the pipeline; the LLM is not called; only logging runs | Saves time and cost; blocked requests are faster |
| D-09 | **Fail closed** on any security component error or timeout | A crash must never open a hole |
| D-10 | **No LLM as the main detector** | Slow, can itself be injected, inconsistent results |
| D-11 | **LLM judge only for borderline scores**, optional, exact `YES`/`NO`, wrapped input, timeout fails closed, never the only signal | Adds context for unclear cases without slowing every request |
| D-12 | **Pretrained Hugging Face classifier**, chosen by testing on our own sets | No time or data to train one; runs locally |
| D-13 | **Rules + classifier + hidden-text diff** combined into one risk score per chunk | No single signal is reliable alone |
| D-14 | **Clean, not only block**: remove only the bad chunk and keep the rest | Keeps documents useful; CB-01 says "blocks or cleans" |
| D-15 | **Console is HTML + CSS + JavaScript served by FastAPI**, matching the Lovable design | Gets the designed look without adding React or Streamlit |
| D-16 | The Lovable and Stitch mockups are **visual references only** | Their sample numbers are not results |
| D-17 | **`send_email` writes to an on-screen Outbox** | Shows what a hijacked AI tried to send without sending anything |
| D-18 | **Fake data only**, everywhere | Safety, and Gemini free-tier data may be used by Google |
| D-19 | **SQLite** for the audit log and evaluation results | Zero setup, one file, queryable |
| D-20 | **YAML** for profiles and rules | Readable, supports comments, easy to swap per company |
| D-21 | **No hard-coded metrics**; the scoreboard shows only real evaluation results | Honesty; the rulebook prohibits misrepresentation |
| D-22 | Approval **cannot override hard rules** (domain allow-list, folder limits, record limits, canary) | Approval relaxes only the taint rule and the goal check |
| D-23 | Tool results returned to the assistant are **untrusted** and go back through Guard A | Attacks can also arrive through tool output |
| D-24 | `/v1/chat/completions` is **text only** (no tool calls) | Proves generality without a second tool system |
| D-25 | Python 3.11+, FastAPI, Pydantic v2 | Mature ML/security libraries; fast, validated API |
| D-26 | **`GEMINI_MODEL` read from `.env` only** | Never hard-coded; user verifies free tier availability before setting |
| D-27 | **First candidate `CLASSIFIER_MODEL` is `protectai/deberta-v3-base-prompt-injection-v2`** | Public, local, fast (noted as English-focused) |
| D-28 | **Email plain vs HTML mismatch via sentence diff** | Sentences in HTML missing from plain text become `is_hidden = True` chunks scored in step 4 |
| D-29 | **`records.json` schema uses key-value dicts with `.example` domains** | Clean lookup structure, no real email domains |
| D-30 | **Spotlighting nonces re-wrapped per request** | Clean untrusted text stored in session is re-wrapped with fresh per-request nonce when building system prompt |
| D-31 | **Canary validation uses exact match + regex `CANARY_[0-9a-f]{12}`** | Checked in step 8 tool args and step 9 output firewall |
| D-32 | **Extractor errors return status `ERROR`** | Corrupt/unparseable files are dropped, request continues fail-closed with remaining inputs |
| D-33 | **`/api/scan` returns complete 10-step trace array** | Steps 1-5 show real results, steps 6-10 and LLM return `status: SKIPPED` with reason `"scan mode (no LLM)"` |

