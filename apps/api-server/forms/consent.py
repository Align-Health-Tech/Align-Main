"""Router-level privacy consent QuestionFields — not graph nodes."""
from __future__ import annotations

from schemas.question_fields import QuestionField


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
