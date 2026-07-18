"""ice answers → ice_idea / ice_concern / ice_expectation (chips + Other)."""
from __future__ import annotations

from typing import Any

from engine.session_state_mappers.selections import join_narrative, selections_for_target
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState

_ICE_TARGETS = (
    "ice_idea",
    "ice_concern",
    "ice_expectation",
)


def map_ice(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for target in _ICE_TARGETS:
        sels = selections_for_target(questions, by_id, target)
        if not sels:
            continue
        # multi_choice — join chips (+ Other free text) into one NarrativeField.
        joined = join_narrative(state, sels)
        if joined is not None:
            updates[target] = joined
    return updates
