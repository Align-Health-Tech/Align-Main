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
| `devise_and_prioritise` | `priority_questions`, `optional_questions`, `redflag_screening`, `presenting_complaint_clarify` |
| `question_generation` | `priority_questions`, `optional_questions`, `redflag_screening`, `ice`, `presenting_complaint_clarify` |
| `nurse_review` | `summary` |
| `translation` | `to_english` |

## Three agents

Implemented as thin wrappers in `agents.py` over `llm_client.run_agent` /
`run_agent_with_tools`:

1. **Classifier** — `run_classifier`
2. **Devise & Prioritise** — `run_devise_and_prioritise` (tools path)
3. **Question Generation** — `run_question_generation`

Helpers: `run_nurse_review_summary_agent`, `translate_to_english`.

Red flag screening is Devise + Question Generation with `phase` /
`prompt_name` = `redflag_screening` — not a fourth agent.

## Stub status

Current `.md` files are **stubs** (option B) with expected output shape and
`TODO` links to Align-Pilot-V2 legacy prompts. Replace stub bodies before
production demos.
