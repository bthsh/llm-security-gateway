# CLAUDE.md: LLM Security Gateway (Team Vantage)

Read this file first, on every task. Then open the doc listed for the task you are doing.

## What we are building

Hackathon: **Hackatopia 2026**, problem **CB-01: LLM firewall against prompt injection**. 24-hour build.

A **general, model-agnostic security gateway** (Python, FastAPI) that sits between users, data sources (web pages, PDFs, emails) and an LLM app. It detects direct and indirect prompt injection, jailbreaks, sensitive-data leaks and tool misuse, and **cleans or blocks** them while **letting normal traffic through**.

For the live demo, a real **Gemini-powered assistant** with three tools (`lookup_record`, `read_document`, `send_email`) sits behind the gateway, and a **web console** (HTML, CSS and JavaScript served by FastAPI) shows every decision.

## The pipeline in one table

| Guard | Step | Name | One line |
|---|---|---|---|
| A | 1 | Normalize | Remove disguises: NFKC, zero-width chars, decode base64/hex/URL |
| A | 2 | Extract | Get all text from PDF/HTML/email, including hidden text |
| A | 3 | Tag provenance | Mark each segment trusted or untrusted |
| A | 4 | Detect | Score each chunk: rules + classifier (+ optional judge for borderline) |
| A | 5 | Decide | Allow, clean (remove chunk) or block (stop early) |
| A | 6 | Spotlight | Wrap untrusted text in random per-request tags |
| A | 7 | Canary + tool scoping | Plant a per-request canary; hide risky tools if the session is tainted |
| - | - | LLM call | Gemini (Ollama optional fallback) |
| B | 8 | Policy engine | Check every tool call before it runs |
| B | 9 | Output firewall | Check the reply: canary, links/images, personal data, secrets |
| - | 10 | Audit log | Record every step of both guards in SQLite |

## Golden rules (never break these)

1. **Build only what `docs/SCOPE.md` lists.** If a feature is not there, ask the user. Do not invent features.
2. **Decisions in `docs/DECISIONS.md` are final.** Do not reopen or "improve" them without the user's approval.
3. **Use the exact names** from `docs/GLOSSARY.md` and `docs/FILE_STRUCTURE.md`: step names, tool names, statuses, file paths.
4. **Fake data only.** No real people, emails, keys or company data, anywhere.
5. **Never hard-code results.** No fixed scores, timings, decisions or metrics in the UI or API. Every value shown comes from a real run. If no value exists yet, show "Not measured yet".
6. **Fail closed.** If a security component errors or times out, risky actions are blocked and the error is logged.
7. **Never fake a detection or a tool call** to make a demo scene work.
8. **Verify every package name, model name and API call** against official documentation before using it. If unsure, say so instead of guessing.
9. **One module per step.** Every step follows the stage contract in `docs/DESIGN.md`.
10. **Tests with every module.** Run `pytest` after every change. Do not move on with failing tests.
11. **Secrets live only in `.env`.** Never commit, print or log `GEMINI_API_KEY`.
12. **Simple, readable code.** The team must be able to explain every line to judges.

## Build order

Follow `docs/TASKS.md`. Short version:

1. Skeleton, config, Pydantic models, audit log
2. Normalize, provenance, rule detection, decide (with early exit)
3. Gemini backend, assistant loop, tools, Outbox
4. Extractors (PDF, HTML, email)
5. Classifier
6. Spotlight, canary, tool scoping
7. Policy engine (with approval flow)
8. Output firewall
9. API endpoints and console UI
10. Test sets and evaluation script
11. Optional: LLM judge, Ollama fallback

## Definition of done for any module

- Follows the stage contract and uses the shared Pydantic models
- Unit tests pass
- Returns a short, human-readable `reason` for every decision
- Measures its own time in milliseconds
- Writes its result to the audit log through the pipeline
- Contains no hard-coded demo values

## Docs map

| Need | Read |
|---|---|
| What is in or out | `docs/SCOPE.md` |
| Why a choice was made | `docs/DECISIONS.md` |
| What a term means | `docs/GLOSSARY.md` |
| How the system fits together | `docs/ARCHITECTURE.md` |
| Where files go | `docs/FILE_STRUCTURE.md` |
| How each step works | `docs/DESIGN.md` |
| Endpoints and JSON | `docs/API.md` |
| Profiles, settings, env vars | `docs/CONFIG.md` |
| The console | `docs/UI.md` |
| Attacks covered | `docs/THREAT_MODEL.md` |
| How to code it well | `docs/BEST_PRACTICES.md` |
| What never to do | `docs/DONTS.md` |
| Tests and metrics | `docs/TEST_PLAN.md` |
| Install and run | `docs/SETUP.md` |
| Demo for judges | `docs/DEMO_PLAN.md` |
| Build checklist | `docs/TASKS.md` |

## Git
- After each checkpoint in docs/TASKS.md passes its tests, run
  git status, confirm .env is not listed, then
  git add -A && git commit -m "<short description>" && git push
- Never commit .env, logs/, data/runtime/ or *.db.
- If .env or a secret appears in git status, stop and tell me.

## When unsure

Check `SCOPE.md`, then `DECISIONS.md`, then `DESIGN.md`. If it is still unclear, **stop and ask the user**. Do not guess.
Add this section to the bottom of AGENTS.md and commit it:

## Progress summaries

After completing each checkpoint in docs/TASKS.md, before moving to
the next one, write a short summary in this exact format and post it
in the chat:

---
CHECKPOINT [number]: [name]
Status: DONE / PARTIAL / BLOCKED

What was built:
- [one line per file or feature completed]

Test results:
- [pass/fail counts, or "no tests yet" if none written]

Is the build on track?
- [YES / NO / BEHIND]
- [one sentence on why, and what was skipped or deferred]

Next checkpoint:
- [name and what it needs from me before starting]

Any decision needed from you:
- [question, or "none"]
---

Rules:
- Write this after every checkpoint, not just when something goes wrong.
- Never skip the "Is the build on track?" line.
- If any step was skipped or deferred, name it explicitly.
- If a decision is needed, stop and wait for my answer before
  continuing to the next checkpoint.
- If the build is BLOCKED, explain what is blocking it and what
  I need to do.