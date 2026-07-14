# Question Generation — presenting complaint clarify

Phrase clarification topics from Devise into QuestionField batch.
Every QuestionField MUST include personalization_note.
Return QuestionGenerationResult.

**Code-enforced (engine `qg_phase_validators`):** each question must be
`kind=single_choice`, **2–5** options, and include an option whose value or
label is `"Other"`. Invalid output raises — do not rely on prompt alone.

TODO: port clarifier option phrasing from presenting-concerns clarifier prompts.
