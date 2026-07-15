# Question Generation — optional

Same as priority but default required=false.
Every QuestionField MUST include personalization_note (why this patient / these options).

### Field discipline — `en_prompt` / `en_label`

`en_prompt` (on QuestionField) and `en_label` (on each QuestionOption):
ONLY set these when session_language (see `context`) is NOT "en" — same
rule as NarrativeField.en_text elsewhere in this schema. These exist for
the clinician dashboard when the patient's session isn't in English. When
session_language is "en", omit both entirely (null) — do not duplicate
`prompt`/`label` text into them.

Return QuestionGenerationResult.

TODO: port from Align-Pilot-V2 `prompts/collect_optional_questions/optional-question-decider.md`
