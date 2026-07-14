"""Shared test helpers for walking graph interrupts (no consent — router-level)."""
from __future__ import annotations

from engine.runner import SessionRunner
from schemas.question_fields import NextStep


def answer_pc_free_text(
    runner: SessionRunner, session_id: str, text: str
) -> NextStep:
    return runner.resume(
        session_id,
        {"answers": [{"question_id": "pc_chief_complaint", "value": text}]},
    )


def answer_body_diagram(
    runner: SessionRunner,
    session_id: str,
    *,
    region_id: str = "Select_RightWrist",
) -> NextStep:
    return runner.resume(session_id, {"region_id": region_id})


def answer_localised_detail_questions(
    runner: SessionRunner, session_id: str
) -> NextStep:
    return runner.resume(
        session_id,
        {
            "answers": [
                {"question_id": "loc_severity", "value": "7"},
                {"question_id": "loc_onset", "value": "twisted it yesterday"},
            ]
        },
    )


def answer_localised_detail(runner: SessionRunner, session_id: str) -> NextStep:
    """Body-diagram tap + severity/onset — lands on priority_questions."""
    step = answer_body_diagram(runner, session_id)
    assert step.phase == "localised_detail"
    assert step.step_type == "question_batch"
    return answer_localised_detail_questions(runner, session_id)


def answer_nl_details(runner: SessionRunner, session_id: str) -> NextStep:
    return runner.resume(
        session_id,
        {
            "answers": [
                {"question_id": "nl_onset", "value": "started last week"},
                {"question_id": "nl_severity", "value": "5"},
                {"question_id": "nl_functional", "value": "4"},
            ]
        },
    )


def walk_to_optional(runner: SessionRunner, session_id: str) -> NextStep:
    """PC localised → detail → priority → redflag(no) → optional."""
    answer_pc_free_text(runner, session_id, "pain in my right wrist")
    answer_localised_detail(runner, session_id)
    runner.resume(
        session_id,
        {"answers": [{"question_id": "meds_q1", "value": "no"}]},
    )
    return runner.resume(
        session_id,
        {
            "answers": [
                {"question_id": "rf_chest_pain", "value": "no"},
                {"question_id": "rf_neuro", "value": "no"},
            ]
        },
    )


def answer_ice(runner: SessionRunner, session_id: str) -> NextStep:
    return runner.resume(
        session_id,
        {
            "answers": [
                {"question_id": "ice_idea", "value": "maybe a sprain"},
                {"question_id": "ice_concern", "value": "worried about fracture"},
                {"question_id": "ice_expectation", "value": "want an X-ray"},
            ]
        },
    )


def snap_values(runner: SessionRunner, session_id: str) -> dict:
    snap = runner._graph.get_state({"configurable": {"thread_id": session_id}})
    return snap.values if isinstance(snap.values, dict) else snap.values.model_dump()
