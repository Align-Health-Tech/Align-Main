# Question Generation — non-localised clarify

Phrase clarification topics from Devise into QuestionField batch.
Every QuestionField MUST include personalization_note.

**Code-enforced (engine `qg_phase_validators`):** each question must be
`kind=single_choice` with option **values** exactly
`["Yes", "No", "I don't know"]` (that order). Invalid output raises.

### Field discipline — `en_prompt` / `en_label`

`en_prompt` (on QuestionField) and `en_label` (on each QuestionOption):
ONLY set these when session_language (see `context`) is NOT "en" — same
rule as NarrativeField.en_text elsewhere in this schema. These exist for
the clinician dashboard when the patient's session isn't in English. When
session_language is "en", omit both entirely (null) — do not duplicate
`prompt`/`label` text into them.

Return QuestionGenerationResult.

TODO: port clarifier phrasing for systemic / non-localised presentations.
