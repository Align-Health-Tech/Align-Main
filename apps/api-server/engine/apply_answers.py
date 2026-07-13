"""Map patient resume answers onto SessionState field updates.

Called after interrupt() returns. Does not talk to LangGraph or the LLM —
only "answer JSON → partial state dict". Pattern E translation lives in
engine.translate (called from free-text narrative builders here).
"""
from __future__ import annotations

from typing import Any

from engine.state_codecs import as_question_fields
from engine.translate import narrative_dump_free_text, narrative_dump_option
from schemas.jsonb_fields import CodedField
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState

_YES = frozenset({True, "yes", "true", "accepted", "Yes", "True"})


def apply_answers(
    state: SessionState,
    answer: Any,
    questions: list[QuestionField] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a partial state update dict from a resume payload.

    Expected answer shape:
      {"answers": [{"question_id": str, "value": str | bool | list}]}
    """
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
    vals = _values_by_target(questions, by_id)
    region = vals.get("body_region")
    laterality = vals.get("laterality")
    severity_raw = vals.get("severity_score")
    onset = vals.get("onset_circumstance")

    updates: dict[str, Any] = {}
    severity: int | None = None
    if severity_raw is not None and str(severity_raw).isdigit():
        severity = int(str(severity_raw))
        updates["severity_score"] = severity

    if region is not None:
        region_s = str(region)
        body = {
            "region_detail": CodedField(
                layman_term=region_s,
                anatomical_term=region_s,
                fhir_system="fake",
                fhir_code=region_s,
            ).model_dump(),
            "laterality": laterality if laterality in ("left", "right", "bilateral") else None,
            "severity_score": severity,
            "sub_region_detail": None,
            "radiation_status": None,
            "character": [],
            "radiation_sites": [],
        }
        updates["body_structures"] = [body]

    if onset is not None and onset != "":
        updates["onset_circumstance"] = narrative_dump_free_text(
            str(onset), session_language=state.session_language
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
        updates["onset_circumstance"] = narrative_dump_free_text(
            str(onset), session_language=state.session_language
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
