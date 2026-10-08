# BEST PRACTICES

## Code
- Type hints everywhere; Pydantic models from `app/models.py` for every data shape.
- Small functions with one job. One step per file.
- Clear names that match `GLOSSARY.md`.
- Every decision returns a short, human-readable `reason`.
- Catch errors inside each step and return `ERROR` with fail-closed behaviour; never crash the request.
- Log with Python `logging`; never `print` secrets or full user documents.
- Configuration only through `app/config.py`; patterns and thresholds only in `config/`.
- Comments explain **why**, not what.

## Security
- `GEMINI_API_KEY` only in `.env`. `.env` is in `.gitignore`. Never log it, never send it to the UI.
- Fake data only. Use `.example` domains for fake companies and emails.
- Validate every input: file type by extension **and** content, size limits, message length.
- Path safety: resolve paths and confirm they stay inside the allowed folder before reading.
- Never `eval`, `exec` or run shell commands on any content.
- Never render untrusted HTML in the UI: insert text with `textContent`, not `innerHTML`.
- Treat everything the LLM produces as untrusted until step 9 has run.
- Approval never overrides hard rules.
- Return generic error messages to clients; details go to the log.
- Pin dependency versions in `requirements.txt` once they work.

## Testing
- Write unit tests with each module, using small fake inputs.
- Test both directions: attacks must be caught **and** normal inputs must pass.
- Keep test doubles (scripted LLM backend) inside `tests/` only.
- Use `/api/scan` (no LLM) for fast detection tests to save Gemini quota.
- Run `pytest` after every change; fix failures before moving on.
- Re-run `tests/run_eval.py` after any threshold or rule change.

## Performance
- Load the classifier and spaCy model **once** at startup, then warm them up with one call.
- Run cheap checks first; skip the classifier when rules already decide.
- Batch chunks into one classifier call.
- Cache classifier and judge results by SHA-256 of the text.
- Early exit on block.
- Record `ms` for every step.

## Gemini usage
- One backend class; model name from config.
- Count calls per request (assistant turns + judge) to stay within free-tier limits.
- Handle 429 with one short retry, then a clear error.
- Never send real data to the free tier.

## UI
- All values from the API; nothing hard-coded.
- Show words with every colour.
- Disable Send while a request runs; show clear errors.
- Keep the look from `UI.md`; do not add panels or pages.

## Git
- Small commits with clear messages.
- Never commit `.env`, `logs/`, `data/runtime/`, model weights.
- Freeze the code about 3 hours before judging; after that, only critical fixes.
