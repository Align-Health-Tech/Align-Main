"""redflag_screening answers → raised_flag_topics."""
from __future__ import annotations

from typing import Any

from engine.session_state_mappers.shared import _YES
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


def map_redflag(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    raised = list(state.raised_flag_topics)
    for q in questions:
        val = by_id.get(q.id)
        if val not in _YES:
            continue
        topic = q.collect_target_id or q.id
        if topic not in raised:
            raised.append(topic)
    return {"raised_flag_topics": raised}
