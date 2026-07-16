"""localised_detail / non_localised_detail score + timing answers."""
from __future__ import annotations

from typing import Any

from engine.helpers.apply.shared import messages_from_answers, values_by_target
from engine.helpers.translate import narrative_dump_option
from engine.static.onset_timing import onset_timing_label
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


def apply_localised_detail(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    """Round-2 severity/onset — region_detail already set by body_diagram."""
    vals = values_by_target(questions, by_id)
    severity_raw = vals.get("severity_score")
    onset = vals.get("onset_circumstance")

    updates: dict[str, Any] = {}
    severity: int | None = None
    if severity_raw is not None and str(severity_raw).isdigit():
        severity = int(str(severity_raw))
        updates["severity_score"] = severity

    if severity is not None and state.body_structures:
        bodies = [dict(b) for b in state.body_structures]
        bodies[0]["severity_score"] = severity
        updates["body_structures"] = bodies

    if onset is not None and onset != "":
        updates["onset_circumstance"] = narrative_dump_option(
            onset_timing_label(str(onset))
        )

    return updates


def apply_non_localised_detail(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    if state.non_localised_category is None:
        return messages_from_answers(questions, by_id)

    vals = values_by_target(questions, by_id)
    updates: dict[str, Any] = {}
    onset = vals.get("onset_circumstance")
    if onset is not None and onset != "":
        updates["onset_circumstance"] = narrative_dump_option(
            onset_timing_label(str(onset))
        )
    sev = vals.get("severity_score")
    if sev is not None and str(sev).isdigit():
        updates["severity_score"] = int(str(sev))
    func = vals.get("functional_impact_score")
    if func is not None and str(func).isdigit():
        updates["functional_impact_score"] = int(str(func))
    return updates
