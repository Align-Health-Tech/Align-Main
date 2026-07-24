"""Router-level post-intake survey QuestionFields — not graph nodes."""
from __future__ import annotations

from schemas.question_fields import QuestionField, QuestionOption


def build_survey_questions() -> list[QuestionField]:
    """Default post-intake survey. Later: load from `Survey.schema` for the org."""
    return [
        QuestionField(
            id="survey_ease",
            kind="single_choice",
            prompt="How easy was this intake to complete?",
            personalization_note="deterministic",
            collect_target_id="survey_ease",
            required=False,
            options=[
                QuestionOption(value="easy", label="Easy"),
                QuestionOption(value="ok", label="OK"),
                QuestionOption(value="hard", label="Hard"),
            ],
        ),
    ]
