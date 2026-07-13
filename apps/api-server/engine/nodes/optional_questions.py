"""optional_questions — Pattern C skippable fake Devise+QG batch."""
from __future__ import annotations

from typing import Any

from langgraph.types import Command, interrupt

from engine.apply_answers import apply_answers
from engine.completed_phases import with_completed
from engine.next_step import build_next_step
from engine.state_codecs import (
    as_question_fields,
    dump_question_fields,
    dump_topic_candidates,
)
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_PHASE = "optional_questions"

fake_optional_qg_call_count = 0


def reset_optional_fakes() -> None:
    global fake_optional_qg_call_count
    fake_optional_qg_call_count = 0


def _generate_optional(
    _state: SessionState,
) -> tuple[list[TopicCandidate], list[QuestionField]]:
    global fake_optional_qg_call_count
    fake_optional_qg_call_count += 1
    topics = [
        TopicCandidate(
            topic="sleep",
            relevance_score=0.5,
            is_red_flag=False,
            source="base_reasoning",
        )
    ]
    questions = [
        QuestionField(
            id="opt_sleep",
            kind="yes_no",
            prompt="Has this been affecting your sleep?",
            personalization_note="fake optional",
            collect_target_id="sleep",
            required=False,
        )
    ]
    return topics, questions


def optional_questions(state: SessionState) -> Command:
    if not state.pending_questions:
        topics, questions = _generate_optional(state)
        return Command(
            update={
                "prioritised_topics": dump_topic_candidates(topics),
                "pending_questions": dump_question_fields(questions),
                "awaiting_phase": _PHASE,
            },
            goto="optional_questions",
        )

    questions = as_question_fields(state.pending_questions)
    answer: Any = interrupt(
        build_next_step(state, questions, phase=_PHASE).model_dump()
    )
    # Skip: patient declines optional batch — still mark phase complete.
    if isinstance(answer, dict) and answer.get("skip"):
        return Command(
            update={
                "turn_number": state.turn_number + 1,
                "pending_questions": [],
                "awaiting_phase": None,
                "completed_phases": with_completed(state, _PHASE),
            },
            goto="ice",
        )

    updates = apply_answers(state, answer, questions)
    return Command(
        update={
            **updates,
            "pending_questions": [],
            "awaiting_phase": None,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="ice",
    )
