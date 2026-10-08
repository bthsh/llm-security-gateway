# DON'TS

Hard "never" rules. If a task seems to need one of these, stop and ask the user.

## Scope
- Don't add features, pages or panels that are not in `SCOPE.md`.
- Don't add a "gateway OFF" mode or an "example" toggle.
- Don't build sidebar pages, SIEM export, forensic export, or enterprise labels.
- Don't switch the console to Streamlit or React.
- Don't introduce another agent framework (LangChain, DeepSeek Harness, etc.).
- Don't reopen decisions in `DECISIONS.md`.

## Honesty
- Don't hard-code scores, decisions, timings, token counts or metrics anywhere.
- Don't show sample numbers from the Lovable or Stitch mockups.
- Don't fake a detection, a tool call, a block or an LLM reply to make a demo work.
- Don't claim a feature in the UI, docs or slides that isn't built and tested.
- Don't add artificial delays to make processing look busier.

## Security
- Don't use real names, emails, phone numbers, IDs or keys. Ever.
- Don't commit, log, print or display `GEMINI_API_KEY`.
- Don't let any tool send real email or make outbound network calls.
- Don't execute, `eval` or render content from files, the LLM or users.
- Don't put untrusted text into the page with `innerHTML`.
- Don't let approval override hard rules.
- Don't trust LLM output, tool output or uploaded files.
- Don't fail open: on error, risky actions are blocked.

## Design
- Don't use an LLM as the main detector.
- Don't call the judge on every chunk; borderline only.
- Don't let the judge's answer be the only signal, or override a high score.
- Don't remove Guard B or move steps 8-9 before the LLM call.
- Don't hard-code thresholds, patterns, domains or profile values in Python.
- Don't duplicate data models; use `app/models.py`.
- Don't use the scripted test backend in the running app.

## Dependencies
- Don't invent package names, model names or API calls. Verify in official docs first.
- Don't use AGPL-licensed libraries (e.g. PyMuPDF) without asking.
- Don't download models at request time; download them beforehand.

## Process
- Don't move on with failing tests.
- Don't make large refactors after the code freeze.
- Don't write code the team can't explain.
