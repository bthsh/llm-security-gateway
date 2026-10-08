# TASKS

Hour 0 = start of building. Tick items off. Stop at each checkpoint and confirm it works before continuing.

## H0-H1 · Setup
- [ ] Repo, `.gitignore`, `.env.example`, `requirements.txt`
- [ ] Folder structure from `FILE_STRUCTURE.md`
- [ ] `app/config.py`, `app/models.py`, empty step modules with `run(ctx)`
- [ ] SQLite audit log (`app/audit/log.py`)
- [ ] Download classifier and spaCy model; check Gemini key

## H1-H4 · Guard A text path
- [ ] Step 1 normalize + tests
- [ ] Step 3 provenance, chunking + tests
- [ ] Rules (`config/rules/injection_patterns.yaml`) + step 4 (rules only) + tests
- [ ] Step 5 decide with early exit + tests
- [ ] `app/pipeline.py` with fail-closed wrapper; `POST /api/scan`
- **Checkpoint 1:** a typed "ignore previous instructions" is BLOCKED via `/api/scan`; a normal question passes.

## H4-H7 · LLM and assistant
- [ ] `app/llm/base.py`, `app/llm/gemini.py`
- [ ] Profiles (both YAML files), fake data, `tools.py` with Outbox
- [ ] Assistant loop (max turns), system prompt builder
- [ ] Step 7 canary + tool scoping, sessions and taint
- [ ] `POST /api/chat`
- **Checkpoint 2:** a normal question gets a real Gemini answer through the full pipeline; trace shows all steps.

## H7-H10 · Extraction and spotlight
- [ ] `scripts/make_samples.py` (poisoned EML, hidden-text PDF, hidden-div HTML, clean files)
- [ ] Step 2 extractors: HTML, email, PDF + tests
- [ ] Hidden-text bonus in step 4; document drop ratio in step 5
- [ ] Step 6 spotlight + tests
- **Checkpoint 3:** the poisoned email is CLEANED, `send_email` hidden, summary still correct.

## H10-H12 · Classifier
- [ ] `classifier.py` (load once, batch, cache, warm-up)
- [ ] Compare 2-3 candidates with `/api/scan`; set `CLASSIFIER_MODEL`
- **Checkpoint 4:** reworded attacks detected; false positives checked on the normal set.

## H12-H15 · Guard B
- [ ] Step 8 policy engine: allow-list, schema, hard rules, canary in args, taint, goal check
- [ ] Approval flow + `POST /api/approve`
- [ ] Step 9 output firewall: canary, decode-then-scan, links/images (incl. reference-style), redaction
- [ ] Layers + `POST /api/layers`, `POST /api/reset`
- **Checkpoint 5:** S-08 to S-14 from `TEST_PLAN.md` pass.

## H15-H18 · Console
- [ ] `ui/index.html`, `styles.css`, `app.js` per `UI.md`
- [ ] All panels fed by the API; empty states; banners
- [ ] Remaining endpoints: health, profiles, samples, outbox, logs, metrics, testset
- **Checkpoint 6:** every demo scene works from the console.

## H18-H20 · Evaluation
- [ ] `attacks.jsonl`, `normal.jsonl` (core sets first, red-team set next)
- [ ] `tests/run_eval.py` (scan and full modes) → `eval_runs` table
- [ ] Tune thresholds and rules; re-run
- **Checkpoint 7:** scoreboard shows real measured numbers.

## H20-H21 · Optional
- [ ] LLM judge (borderline only)
- [ ] Ollama fallback
- [ ] `/v1/chat/completions` (if not already done) + prepared `curl`

## H21 · Code freeze

## H21-H24 · Delivery
- [ ] Final presentation named after the team ("Team Vantage.pptx", per rulebook format)
- [ ] Backup screen recording
- [ ] Three timed rehearsals (`DEMO_PLAN.md`)
- [ ] Push final code; repository link ready

## Split for 4 people

| Person | Owns |
|---|---|
| 1 · Backend lead | `config.py`, `models.py`, `pipeline.py`, `sessions.py`, LLM backends, assistant loop, API |
| 2 · Detection | Steps 1, 3, 4, 5, chunking, rules, classifier, judge |
| 3 · Extraction + Guard B | Step 2 extractors, steps 6-9, sample files |
| 4 · UI + proof | Console, test sets, `run_eval.py`, demo, slides |

Every person must be able to explain their part to the judges.
