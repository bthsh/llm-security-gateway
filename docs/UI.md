# UI: the console

One page, HTML + CSS + JavaScript in `ui/`, served by FastAPI at `/`. Visual reference: the Lovable mockup (clean light theme, three columns, scoreboard strip). **Use it as a look reference only. Its sample values are not data.**

## Layout

```
┌───────────────────────────────────────────────────────────────────────────┐
│ TOP BAR  LLM Security Gateway | Profile ▾ | Gemini ● Connected | Layers ▾ | Reset │
├──────────────────┬───────────────────────────────┬────────────────────────┤
│ ATTACK LAB       │ PIPELINE                      │ RESULT                 │
│ Chat/Upload/Paste│ GUARD A  rows 1-7             │ Decision banner        │
│ input + Send     │ Gemini call row               │ Before / After         │
│ Sample files     │ GUARD B  rows 8-9             │ AI reply               │
│                  │ Audit log row 10              │ Tool calls             │
│                  │                               │ Outbox | Redactions    │
│                  │                               │ Approval card (if any) │
│                  │                               │ [Add to test set]      │
├──────────────────┴───────────────────────────────┴────────────────────────┤
│ SCOREBOARD  Attacks caught | Normal wrongly blocked | Gateway ms | LLM time │
└───────────────────────────────────────────────────────────────────────────┘
```
At narrow widths the columns stack (Attack Lab, Pipeline, Result).

## Top bar
- Title "LLM Security Gateway", subtitle "Prompt injection defense console"
- **Profile** dropdown from `GET /api/profiles`. Changing it resets the session.
- **Backend status** pill from `GET /api/health`: "Gemini · Connected" (green dot) or "Gemini · Unavailable" (red dot, with words)
- **Layers** dropdown: switches for Classifier, LLM judge, Tool scoping, Policy engine, Output firewall → `POST /api/layers`
- **Reset** → `POST /api/reset`, clears all panels

## Attack Lab (left)
- Tabs: **Chat** (message box + attach file button), **Upload** (file picker), **Paste** (large text area, sent as a `.txt` attachment)
- Shows the user's message and attachment chips after sending
- **Send** button. Disabled while a request is running; shows "Checking..." text
- **Sample files** list from `GET /api/samples` with a type tag (EML, PDF, HTML). Clicking one attaches it.

## Pipeline (middle)
- Two section headers: "GUARD A · before the AI" and "GUARD B · after the AI"
- One row per trace entry, in order: number, step name, **status badge with the word**, short reason, time in ms
- The LLM row sits between the guards: "Gemini call · 1.2 s" (real value)
- Row 10 "Audit log" at the bottom
- Flagged/blocked rows show the reason in bold; passed rows keep it short
- Early exit: rows 6-9 show `SKIPPED`
- Rows render from the response. No fake delays: if rows animate in, use a short fixed reveal (≤ 60 ms per row) and always show the **real** `ms` values.
- Empty state before the first request: "Send a message or load a sample file to see the pipeline."

## Result (right)
- **Decision banner**: word + colour, e.g. "CLEANED · answered safely", "BLOCKED · request stopped at step 5", "BLOCKED ACTION · AI was tricked, action stopped", "NEEDS APPROVAL"
- **Before / After**: kept text, then removed text struck through with a label "Removed (hidden text)" and its reason. Only shown if something was removed.
- **AI reply**: the final reply after step 9
- **Tool calls**: each call in monospace with status (EXECUTED / BLOCKED / PENDING_APPROVAL / APPROVED / DENIED) and reason. If tools were hidden: "send_email was not offered because the session is tainted."
- **Outbox**: emails the assistant "sent" this session, or "Empty · nothing was sent"
- **Redactions**: type, masked preview, replacement; or "None"
- **Approval card** only when `pending_action` is present: "The AI wants to send an email to <masked>. Approve?" with **Approve** and **Deny** buttons → `POST /api/approve`
- **Add to test set** → `POST /api/testset`, then a short confirmation

## Scoreboard (bottom)
From `GET /api/metrics`:
- Attacks caught `X / Y`, Normal messages wrongly blocked `Z / N`, Median gateway time `N ms`, Median LLM time `N s`
- If `measured: false`: every card shows "Not measured yet"
- Small caption with the time of the evaluation run

## Banners
- Any layer off → yellow banner "Demo mode: <layer> is OFF"
- LLM rate limit or error → red banner with the message from the API

## Visual style
- Light theme: page background light grey, white panels, dark text, 8 px radius, generous spacing
- Fonts: IBM Plex Sans (UI) and IBM Plex Mono (scores, times, tool calls) from Google Fonts, with fallbacks `system-ui, sans-serif` and `ui-monospace, monospace`
- One blue accent for interactive elements
- Status colours, always paired with the word:
  - PASSED: green · FLAGGED: amber · CLEANED: amber/orange · BLOCKED: red · SKIPPED: grey · INFO: slate blue · LOGGED: grey · ERROR: red outline
- Colours must also differ in lightness. Text contrast at least 4.5:1.
- Body text at least 15 px; readable on a projector
- No gradients, no emoji, no decorative animation

## Accessibility
- Real `<button>`, `<input>`, `<label>`, `<select>` elements
- `aria-live="polite"` on the decision banner
- Icon-only buttons have `aria-label`
- Keyboard: Tab through controls, Enter sends

## Must NOT appear
- "Gateway OFF" switch or "Example: blocked action" switch
- "Static demo" footer
- Sidebar navigation, version tags, session/trace IDs as decoration, policy names, "Re-run evaluation", "Export forensic JSON", "SIEM", "Sandbox verified", token counts, percentages or "this week" text
- Any hard-coded result, score, time or metric
