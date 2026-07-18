"""Map patient resume answers onto SessionState field updates.

Called after interrupt() returns. Does not talk to LangGraph or the LLM —
only "answer JSON → partial state dict". Pattern E translation lives in
engine.session_state_mappers.narrative (via agent_bridge.translate_to_english).

Body-diagram resumes use ``{"region_id": "..."}`` (not the QuestionField
``answers`` list) — routed to ``patient.body_diagram.map_body_diagram``.

Consent / survey are router-level (not graph phases) — they do not flow
through this helper.

Phase-specific mappers live under ``patient/``.
"""
from __future__ import annotations

from typing import Any

from engine.session_state_mappers.patient.body_diagram import (
    map_body_diagram,
)
from engine.session_state_mappers.patient.detail import (
    map_localised_detail,
    map_non_localised_detail,
)
from engine.session_state_mappers.patient.ice import map_ice
from engine.session_state_mappers.patient.optional import (
    map_optional_questions,
)
from engine.session_state_mappers.patient.presenting_complaint import (
    map_presenting_complaint,
)
from engine.session_state_mappers.patient.priority import (
    map_priority_questions,
)
from engine.session_state_mappers.patient.redflag import map_redflag
from engine.helpers.state_codecs import as_question_fields
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


def map_patient_answers(
    state: SessionState,
    answer: Any,
    questions: list[QuestionField] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a partial state update dict from a resume payload.

    Expected answer shape (question_batch):
      {"answers": [{"question_id": str, "value": str | bool | list}]}

    Body-diagram shape ``{"region_id": "..."}`` is handled via ``map_body_diagram``.
    """
    if isinstance(answer, dict) and "region_id" in answer:
        return map_body_diagram(state, answer)

    typed = (
        questions
        if questions and isinstance(questions[0], QuestionField)
        else as_question_fields(questions)  # type: ignore[arg-type]
    )
    payload = answer if isinstance(answer, dict) else {}
    raw_answers = payload.get("answers") or []
    by_id = {
        a["question_id"]: a.get("value")
        for a in raw_answers
        if isinstance(a, dict) and "question_id" in a
    }

    updates: dict[str, Any] = {
        "turn_number": state.turn_number + 1,
    }

    phase = state.awaiting_phase
    if phase == "presenting_complaint":
        updates.update(map_presenting_complaint(state, typed, by_id))
    elif phase == "localised_detail":
        updates.update(map_localised_detail(state, typed, by_id))
    elif phase == "non_localised_detail":
        updates.update(map_non_localised_detail(state, typed, by_id))
    elif phase == "redflag_screening":
        updates.update(map_redflag(state, typed, by_id))
    elif phase == "ice":
        updates.update(map_ice(state, typed, by_id))
    elif phase == "priority_questions":
        updates.update(map_priority_questions(state, typed, by_id))
    elif phase == "optional_questions":
        updates.update(map_optional_questions(state, typed, by_id))

    return updates
