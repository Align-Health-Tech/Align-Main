"""ice — Pattern C minus devise; free-text idea / concern / expectation."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.apply_answers import apply_answers
from engine.completed_phases import with_completed
from engine.next_step import build_next_step
from engine.state_codecs import as_question_fields, dump_question_fields
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState

_PHASE = "ice"

fake_ice_qg_call_count = 0


def reset_ice_fakes() -> None:
    global fake_ice_qg_call_count
    fake_ice_qg_call_count = 0


def _generate_ice(_state: SessionState) -> list[QuestionField]:
    global fake_ice_qg_call_count
    fake_ice_qg_call_count += 1
    return [
        QuestionField(
            id="ice_idea",
            kind="free_text",
            prompt="What do you think is going on?",
            personalization_note="fake ice",
            collect_target_id="ice_idea",
        ),
        QuestionField(
            id="ice_concern",
            kind="free_text",
            prompt="What worries you most about this?",
            personalization_note="fake ice",
            collect_target_id="ice_concern",
        ),
        QuestionField(
            id="ice_expectation",
            kind="free_text",
            prompt="What are you hoping we can do today?",
            personalization_note="fake ice",
            collect_target_id="ice_expectation",
        ),
    ]


def ice(state: SessionState) -> Command:
    if not state.pending_questions:
        return Command(
            update={
                "pending_questions": dump_question_fields(_generate_ice(state)),
                "awaiting_phase": _PHASE,
            },
            goto="ice",
        )

    questions = as_question_fields(state.pending_questions)
    answer = interrupt(build_next_step(state, questions, phase=_PHASE).model_dump())
    updates = apply_answers(state, answer, questions)
    return Command(
        update={
            **updates,
            "pending_questions": [],
            "awaiting_phase": None,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="review",
    )
