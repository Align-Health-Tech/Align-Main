"""Map patient resume answers onto SessionState field updates.

Called after interrupt() returns. Does not talk to LangGraph or the LLM —
only "answer JSON → partial state dict". Pattern E translation lives in
engine.helpers.translate (via agent_bridge.translate_to_english).

Body-diagram resumes use ``{"region_id": "..."}`` (not the QuestionField
``answers`` list) — routed inside ``apply_answers`` to ``_apply_body_diagram``.
"""
from __future__ import annotations

from typing import Any

from engine.helpers.state_codecs import as_question_fields
from engine.helpers.translate import narrative_dump_free_text, narrative_dump_option
from engine.static.onset_timing import onset_timing_label
from engine.static.body_diagram_catalogue import laterality_for_region_id, resolve_coding
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState

_YES = frozenset({True, "yes", "true", "accepted", "Yes", "True"})


def apply_answers(
    state: SessionState,
    answer: Any,
    questions: list[QuestionField] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a partial state update dict from a resume payload.

    Expected answer shape (question_batch / consent / survey):
      {"answers": [{"question_id": str, "value": str | bool | list}]}

    Body-diagram shape ``{"region_id": "..."}`` is handled via ``_apply_body_diagram``.
    """
    if isinstance(answer, dict) and "region_id" in answer:
        return _apply_body_diagram(state, answer)

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
    if phase == "consent":
        updates.update(_apply_consent(state, typed, by_id))
    elif phase == "presenting_complaint":
        updates.update(_apply_presenting_complaint(state, typed, by_id))
    elif phase == "localised_detail":
        updates.update(_apply_localised_detail(state, typed, by_id))
    elif phase == "non_localised_detail":
        updates.update(_apply_non_localised_detail(state, typed, by_id))
    elif phase == "redflag_screening":
        updates.update(_apply_redflag(state, typed, by_id))
    elif phase == "ice":
        updates.update(_apply_ice(state, typed, by_id))
    # priority / optional / survey: turn_number only for current fakes

    return updates


def _apply_body_diagram(state: SessionState, answer: Any) -> dict[str, Any]:
    """Handle body_diagram resume: ``{"region_id": "Select_RightAnkle"}``."""
    payload = answer if isinstance(answer, dict) else {}
    region_id = payload.get("region_id")
    if not isinstance(region_id, str) or not region_id.strip():
        raise ValueError(f"body_diagram answer missing region_id: {answer!r}")

    coding = resolve_coding(region_id)
    if coding is None:
        raise ValueError(f"Unrecognised region_id from client: {region_id!r}")

    return {
        "turn_number": state.turn_number + 1,
        "body_structures": [
            {
                "region_detail": coding.model_dump(),
                "laterality": laterality_for_region_id(region_id),
                "severity_score": None,
                "sub_region_detail": None,
                "radiation_status": None,
                "character": [],
                "radiation_sites": [],
            }
        ],
    }


def _apply_consent(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    accepted = list[str](state.consents_accepted)
    for q in questions:
        if q.kind != "consent_accept":
            continue
        if by_id.get(q.id) in _YES:
            accepted.append(q.id)
    return {"consents_accepted": accepted}


def _apply_presenting_complaint(
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

    return _messages_from_answers(questions, by_id)


def _apply_localised_detail(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    """Round-2 severity/onset — region_detail already set by body_diagram."""
    vals = _values_by_target(questions, by_id)
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


def _apply_non_localised_detail(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    if state.non_localised_category is None:
        return _messages_from_answers(questions, by_id)

    vals = _values_by_target(questions, by_id)
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


def _apply_redflag(
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


def _apply_ice(
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


def _values_by_target(
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for q in questions:
        if q.collect_target_id is None:
            continue
        if q.id not in by_id:
            continue
        out[q.collect_target_id] = by_id[q.id]
    return out


def _messages_from_answers(
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    new_msgs: list[dict[str, str]] = []
    for q in questions:
        val = by_id.get(q.id)
        if val is None or val == "":
            continue
        text = val if isinstance(val, str) else str(val)
        new_msgs.append({"role": "user", "content": f"{q.prompt} {text}"})
    if not new_msgs:
        return {}
    return {"messages": new_msgs}
