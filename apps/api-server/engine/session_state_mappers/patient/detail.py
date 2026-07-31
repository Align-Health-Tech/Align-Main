"""localised_detail / non_localised_detail score + duration answers."""
from __future__ import annotations

from typing import Any

from engine.session_state_mappers.narrative import (
    narrative_dump_free_text,
    narrative_dump_option,
)
from engine.session_state_mappers.selections import selections_for_target
from engine.session_state_mappers.shared import messages_from_answers, values_by_target
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


def map_localised_detail(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    """Round-2 severity/duration — region_detail already set by body_diagram."""
    vals = values_by_target(questions, by_id)
    severity_raw = vals.get("severity_score")

    updates: dict[str, Any] = {}
    severity: int | None = None
    if severity_raw is not None and str(severity_raw).isdigit():
        severity = int(str(severity_raw))
        updates["severity_score"] = severity

    if severity is not None and state.body_structures:
        bodies = [dict(b) for b in state.body_structures]
        bodies[0]["severity_score"] = severity
        updates["body_structures"] = bodies

    updates.update(_duration_updates(state, questions, by_id))
    return updates


def map_non_localised_detail(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    if state.non_localised_category is None:
        return messages_from_answers(questions, by_id)

    vals = values_by_target(questions, by_id)
    updates: dict[str, Any] = {}
    sev = vals.get("severity_score")
    if sev is not None and str(sev).isdigit():
        updates["severity_score"] = int(str(sev))
    func = vals.get("functional_impact_score")
    if func is not None and str(func).isdigit():
        updates["functional_impact_score"] = int(str(func))
    updates.update(_duration_updates(state, questions, by_id))
    return updates


def _duration_updates(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    sels = selections_for_target(questions, by_id, "duration")
    if not sels:
        return {}
    selection = sels[0]
    if selection.is_free:
        return {
            "duration": narrative_dump_free_text(
                selection.text, session_language=state.session_language
            )
        }
    return {
        "duration": narrative_dump_option(
            selection.text, en_label=selection.en_text
        )
    }
