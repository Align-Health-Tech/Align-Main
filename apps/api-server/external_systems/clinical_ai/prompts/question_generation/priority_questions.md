# Question Generation — priority

Turn prioritised_topics + eligible_targets into QuestionField list (max from input).
Use suggested_options / free_text_policy from eligible_targets.
Default required=true.

Return QuestionGenerationResult: {reason, questions}.

TODO: port phrasing from Align-Pilot-V2 `prompts/devise_priority_questions/priority-question-generator.md`
