# GLOSSARY

Use these exact terms in code, docs and UI.

| Term | Meaning |
|---|---|
| **Gateway** | Our product: the service that runs the 10-step pipeline in front of an LLM |
| **Assistant** | The Gemini-powered chatbot the gateway protects. Not our product; it exists so the gateway has something to protect. |
| **Guard A** | Steps 1-7. Runs before the LLM. Checks what goes in. |
| **Guard B** | Steps 8-9. Runs after the LLM answers. Checks what the AI tries to do and say. |
| **Step 10 / Audit log** | Records the result of every step of both guards |
| **Pipeline** | The full sequence: Guard A, LLM call, Guard B, audit log |
| **Segment** | One piece of text with its source and trust level (for example the user message, or the HTML part of an email) |
| **Chunk** | A slice of a segment small enough for the classifier. Scoring and cleaning happen per chunk. |
| **Source** | Where text came from: `system`, `user`, `document`, `web`, `email`, `tool_result` |
| **Trusted** | `system` and `user` segments |
| **Untrusted** | `document`, `web`, `email`, `tool_result` segments |
| **Provenance** | The source and trust label attached to every segment (step 3) |
| **Hidden text** | Text a human would not see (white, tiny, off-page, `display:none`, comments, metadata) but the AI would read |
| **Visible-vs-hidden diff** | The difference between what a human sees and what was extracted. Non-empty diff is a risk signal. |
| **Risk score** | A number from 0 to 1 for each chunk, from rules, the classifier and the hidden-text bonus |
| **Borderline** | A score between the lower and upper thresholds. May go to the judge. |
| **Judge** | Optional Gemini check for borderline chunks. Answers exactly `YES` or `NO`. Advisory only. |
| **Allow** | Keep the chunk or request as it is |
| **Clean** | Remove only the flagged chunk and keep the rest |
| **Block** | Stop the request. Early exit: the LLM is not called. |
| **Early exit** | When Guard A blocks, steps 6-9 are SKIPPED and only logging runs |
| **Fail closed** | On error or timeout, treat the item as risky: block risky actions, remove borderline chunks |
| **Spotlight** | Wrapping untrusted text in `<data_xxxxxxxx>` tags with a random per-request token, plus an instruction that this is data, not commands |
| **Nonce** | The random per-request token used in spotlight tags |
| **Canary** | A random per-request fake secret (`CANARY_xxxxxxxxxxxx`) placed in the system prompt. If it appears in a reply or tool argument, the system prompt leaked. |
| **Taint / tainted session** | A session that has seen untrusted content or an unresolved borderline user message. Stays tainted until reset. |
| **Tool scoping** | Removing risky tools from the list offered to the LLM when the session is tainted (step 7) |
| **Risky tool** | A tool with outside effect. In our profiles: `send_email`. |
| **Policy engine** | Step 8: checks each tool call (allow-list, arguments, canary, taint rule, goal check, approval) |
| **Goal-consistency check** | Does the tool call match what the user asked for? Uses keyword intents from the profile. |
| **Approval** | A pending tool call the user must approve or deny in the console. Cannot override hard rules. |
| **Output firewall** | Step 9: checks the reply for the canary, external links and images, personal data and secrets |
| **Reference-style markdown** | `![alt][ref]` plus a separate `[ref]: https://...` line. The trick EchoLeak used to slip past link filters. |
| **Outbox** | On-screen list of emails the assistant sent. Nothing leaves the machine. |
| **Profile** | A YAML file with one company's rules, tools, data and thresholds |
| **Layers** | Console switches that turn a protection layer off for demonstration: classifier, judge, tool scoping, policy engine, output firewall |
| **Detected** | An attack that Guard A flagged, cleaned or blocked |
| **Contained** | An attack that caused no damage: no forbidden tool ran, no canary, secret or external link reached the user |
| **False positive** | A normal request that was blocked or had content wrongly removed |

## Status values

**Step status:** `PASSED`, `FLAGGED`, `CLEANED`, `BLOCKED`, `SKIPPED`, `INFO`, `LOGGED`, `ERROR`

**Request decision:** `ALLOWED`, `CLEANED`, `BLOCKED`, `BLOCKED_ACTION`, `NEEDS_APPROVAL`

**Tool call status:** `EXECUTED`, `BLOCKED`, `PENDING_APPROVAL`, `APPROVED`, `DENIED`

## Names that must match everywhere

- Tools: `lookup_record`, `read_document`, `send_email`
- Profiles: `customer_support` ("Customer Support"), `finance_hr` ("Finance/HR")
- Steps: `normalize`, `extract`, `provenance`, `detect`, `decide`, `spotlight`, `canary_tools`, `llm`, `policy`, `output_firewall`, `audit`
