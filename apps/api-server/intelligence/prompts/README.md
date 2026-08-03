# clinical_ai prompts

Prompt text lives here as markdown. Agents load files at runtime via
`load_prompt(category, phase)` — editing wording does not require Python changes.

## Layout

```text
prompts/
├── classifier/{phase}.md
├── devise_and_prioritise/{phase}.md
├── question_generation/{phase}.md
├── nurse_review/{phase}.md
└── translation/{phase}.md
```

| category | phases |
| -------- | ------ |
| `classifier` | `presenting_complaint`, `non_localised_categoriser` |
| `devise_and_prioritise` | `priority_questions`, `optional_questions`, `redflag_screening`, `presenting_complaint_clarify`, `non_localised_clarify` |
| `question_generation` | `priority_questions`, `optional_questions`, `redflag_screening`, `ice`, `duration`, `presenting_complaint_clarify`, `non_localised_clarify` |
| `nurse_review` | `summary` |
| `translation` | `to_english` |

## Three agents

Implemented as thin wrappers in `agents.py` over `llm_client.run_agent`:

1. **Classifier** — `run_classifier`
2. **Devise & Prioritise** — `run_devise_and_prioritise`
3. **Question Generation** — `run_question_generation`
   (`QuestionField.personalization_note` required — do not blind-copy registry options)

Helpers: `run_nurse_review_summary_agent`, `translate_to_english`.

Red flag screening is Devise + Question Generation with `phase` /
`prompt_name` = `redflag_screening` — not a fourth agent.

Priority and red-flag Devise use one forced `web_search` tool round. The tool
deterministically ranks the committed Healthify then Health NZ URL catalogues
and concurrently fetches up to three HTML sources. QG receives only candidate
metadata and validated evidence URLs; it does not receive page text or refetch.
Optional and clarification Devise phases remain reasoning-only.

Evidence-enabled prompts require original paraphrasing and synthesis. Direct
quotes are limited to 14 words and one quote per referenced source.

## Port status

| Status | Prompts |
| ------ | ------- |
| **Ported** (Azure smoked) | `classifier/presenting_complaint`, `devise_and_prioritise` + `question_generation` for `presenting_complaint_clarify`, `non_localised_categoriser` / `non_localised_clarify`, `priority_questions`, `redflag_screening`, `optional_questions`; `question_generation/ice`, `question_generation/duration` (smoke: `smoke_duration/`) (QG-only; smoke: `smoke_optional_and_ice/`); `nurse_review/summary` (single agent; smoke: `smoke_nurse_review/`); `translation/to_english` (Pattern E; smoke: `smoke_translation/`) |
## Dual track

| Track | Azure? | Where |
| ----- | ------ | ----- |
| Graph / Option-2 tests | **No** — patch `engine.agent_bridge.run_*` via `tests/mock_clinical_ai.py` | CI / `npm test` |
| Prompt smoke | **Yes** — one local smoke invocation per ported prompt | Manual only; never required in CI |

An evidence-enabled Devise smoke invocation contains two Azure model requests
around exactly one tool call: the first selects the concise clinical query and
the second produces the final structured candidates from the tool result.
This is still one Devise invocation from the caller's perspective.

Order-based classifier scripts use `side_effect=[...]`. Phase/prompt_name
Devise+QG mocks use `side_effect=function` branching on phase — do not migrate
those with a flat call-order list.
