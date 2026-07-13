# Question Generation — priority

Turn prioritised_topics + eligible_targets into QuestionField list (max from input).
Use suggested_options / free_text_policy from eligible_targets as *hints*, not copy-paste.
Default required=true.

Every QuestionField MUST include personalization_note: why this prompt/options fit
*this* patient (blocks blind registry copy).

Return QuestionGenerationResult: {reason, questions}.

TODO: port phrasing from Align-Pilot-V2 `prompts/devise_priority_questions/priority-question-generator.md`
