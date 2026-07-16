"""ice answers → ice_idea / ice_concern / ice_expectation."""
from __future__ import annotations

from typing import Any

from engine.helpers.translate import narrative_dump_free_text, narrative_dump_option
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


def apply_ice(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for q in questions:
        target = q.collect_target_id
        if target not in ("ice_idea", "ice_concern", "ice_expectation"):
            continue
        val = by_id.get(q.id)
        if val is None or val == "":
            continue
        text = val if isinstance(val, str) else str(val)
        if q.kind == "free_text":
            updates[target] = narrative_dump_free_text(
                text, session_language=state.session_language
            )
        else:
            updates[target] = narrative_dump_option(text)
    return updates
