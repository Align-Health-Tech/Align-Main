# Question Generation — redflag

Phrase red-flag topics as Likert-style questions (No / Mild / Moderate / Severe) or yes/no as appropriate.
Every QuestionField MUST include personalization_note.

### Field discipline — `en_prompt` / `en_label`

`en_prompt` (on QuestionField) and `en_label` (on each QuestionOption):
ONLY set these when session_language (see `context`) is NOT "en" — same
rule as NarrativeField.en_text elsewhere in this schema. These exist for
the clinician dashboard when the patient's session isn't in English. When
session_language is "en", omit both entirely (null) — do not duplicate
`prompt`/`label` text into them.

Return QuestionGenerationResult.

TODO: port from Align-Pilot-V2 red-flag inferrer / chain synthesizer prompts (phrasing only).
