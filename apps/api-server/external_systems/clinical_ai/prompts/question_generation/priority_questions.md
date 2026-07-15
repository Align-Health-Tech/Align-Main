# Question Generation — priority

Turn prioritised_topics + eligible_targets into QuestionField list (max from input).
Use suggested_options / free_text_policy from eligible_targets as *hints*, not copy-paste.
Default required=true.

Every QuestionField MUST include personalization_note: why this prompt/options fit
*this* patient (blocks blind registry copy).

### Field discipline — `en_prompt` / `en_label`

`en_prompt` (on QuestionField) and `en_label` (on each QuestionOption):
ONLY set these when session_language (see `context`) is NOT "en" — same
rule as NarrativeField.en_text elsewhere in this schema. These exist for
the clinician dashboard when the patient's session isn't in English. When
session_language is "en", omit both entirely (null) — do not duplicate
`prompt`/`label` text into them.

Return QuestionGenerationResult: {reason, questions}.

TODO: port phrasing from Align-Pilot-V2 `prompts/devise_priority_questions/priority-question-generator.md`
