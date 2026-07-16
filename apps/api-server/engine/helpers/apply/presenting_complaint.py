"""presenting_complaint answers → chief_complaint / clarify messages."""
from __future__ import annotations

from typing import Any

from engine.helpers.apply.shared import messages_from_answers
from engine.helpers.translate import narrative_dump_free_text
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


def apply_presenting_complaint(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    if state.chief_complaint is None:
        for q in questions:
            if q.collect_target_id != "chief_complaint":
                continue
            val = by_id.get(q.id)
            if val is None or val == "":
                continue
            text = val if isinstance(val, str) else str(val)
            return {
                "chief_complaint": narrative_dump_free_text(
                    text, session_language=state.session_language
                ),
                "messages": [{"role": "user", "content": text}],
            }
        return {}

    return messages_from_answers(questions, by_id)
