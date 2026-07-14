# Question Generation — non-localised clarify

Phrase clarification topics from Devise into QuestionField batch.
Every QuestionField MUST include personalization_note.
Return QuestionGenerationResult.

**Code-enforced (engine `qg_phase_validators`):** each question must be
`kind=single_choice` with option **values** exactly
`["Yes", "No", "I don't know"]` (that order). Invalid output raises.

TODO: port clarifier phrasing for systemic / non-localised presentations.
