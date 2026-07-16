"""Map patient resume answers onto SessionState field updates.

Called after interrupt() returns. Does not talk to LangGraph or the LLM —
only "answer JSON → partial state dict". Pattern E translation lives in
engine.helpers.translate (via agent_bridge.translate_to_english).

Body-diagram resumes use ``{"region_id": "..."}`` (not the QuestionField
``answers`` list) — routed to ``body_diagram.apply_body_diagram``.

Consent / survey are router-level (not graph phases) — they do not flow
through this helper.

Phase-specific mappers live in sibling modules under ``engine.helpers.apply``.
"""
from __future__ import annotations

from typing import Any

from engine.helpers.apply.body_diagram import apply_body_diagram
from engine.helpers.apply.detail import (
    apply_localised_detail,
    apply_non_localised_detail,
)
from engine.helpers.apply.ice import apply_ice
from engine.helpers.apply.presenting_complaint import apply_presenting_complaint
from engine.helpers.apply.priority import apply_priority_questions
from engine.helpers.apply.redflag import apply_redflag
from engine.helpers.state_codecs import as_question_fields
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


def apply_answers(
    state: SessionState,
    answer: Any,
    questions: list[QuestionField] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a partial state update dict from a resume payload.

    Expected answer shape (question_batch):
      {"answers": [{"question_id": str, "value": str | bool | list}]}

    Body-diagram shape ``{"region_id": "..."}`` is handled via ``apply_body_diagram``.
    """
    if isinstance(answer, dict) and "region_id" in answer:
        return apply_body_diagram(state, answer)

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
        updates.update(apply_presenting_complaint(state, typed, by_id))
    elif phase == "localised_detail":
        updates.update(apply_localised_detail(state, typed, by_id))
    elif phase == "non_localised_detail":
        updates.update(apply_non_localised_detail(state, typed, by_id))
    elif phase == "redflag_screening":
        updates.update(apply_redflag(state, typed, by_id))
    elif phase == "ice":
        updates.update(apply_ice(state, typed, by_id))
    elif phase == "priority_questions":
        updates.update(apply_priority_questions(state, typed, by_id))
    # optional: turn_number only until that apply path is ported

    return updates
