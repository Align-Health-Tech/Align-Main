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
| `question_generation` | `priority_questions`, `optional_questions`, `redflag_screening`, `ice`, `presenting_complaint_clarify`, `non_localised_clarify` |
| `nurse_review` | `summary` |
| `translation` | `to_english` |

## Three agents

Implemented as thin wrappers in `agents.py` over `llm_client.run_agent` /
`run_agent_with_tools`:

1. **Classifier** — `run_classifier`
2. **Devise & Prioritise** — `run_devise_and_prioritise` (tools path)
3. **Question Generation** — `run_question_generation`
   (`QuestionField.personalization_note` required — do not blind-copy registry options)

Helpers: `run_nurse_review_summary_agent`, `translate_to_english`.

Red flag screening is Devise + Question Generation with `phase` /
`prompt_name` = `redflag_screening` — not a fourth agent.

## Port status

| Status | Prompts |
| ------ | ------- |
| **Ported** (Azure smokeed) | `classifier/presenting_complaint`, `devise_and_prioritise/presenting_complaint_clarify`, `question_generation/presenting_complaint_clarify` |
| **Still stubs** | Remaining classifier / Devise / QG / nurse_review / translation `.md` files — expected output shape + `TODO` links to Align-Pilot-V2. Replace before production demos. |

## Dual track (M5)

| Track | Azure? | Where |
| ----- | ------ | ----- |
| Graph / Option-2 tests | **No** — patch `engine.helpers.agent_bridge.run_*` via `tests/mock_clinical_ai.py` | CI / `npm test` |
| Prompt smoke | **Yes** — one local Azure call per ported prompt | Manual only; never required in CI |

Order-based classifier scripts use `side_effect=[...]`. Phase/prompt_name
Devise+QG mocks use `side_effect=function` branching on phase — do not migrate
those with a flat call-order list.
