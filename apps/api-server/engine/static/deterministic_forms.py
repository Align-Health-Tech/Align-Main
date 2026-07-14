"""Router-level deterministic form builders — not graph nodes.

Called directly by `routers/session.py` once that exists. Never registered
on the LangGraph topology and never reached via `graph.invoke`.

This module only builds `list[QuestionField]`. Wrap into NextStep via
`engine.next_step`:

- Consent (no SessionState yet):
  `build_next_step_raw(0, build_consent_questions(), phase="consent")`
- Survey (graph already complete, state available):
  `build_next_step(state, build_survey_questions(), phase="survey")`

See `docs/structures/ROUTER_SPEC.md`.
"""
from __future__ import annotations

from schemas.question_fields import QuestionField, QuestionOption


def build_consent_questions() -> list[QuestionField]:
    """Fixed privacy consent item(s)."""
    return [
        QuestionField(
            id="consent_privacy",
            kind="consent_accept",
            prompt="I agree to Align processing my health information for this visit.",
            personalization_note="deterministic",
            collect_target_id="consent_privacy",
        ),
    ]


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
