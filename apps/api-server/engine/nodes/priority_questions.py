"""priority_questions — Pattern C fake Devise+QG batch."""
from __future__ import annotations

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

_PHASE = "priority_questions"

fake_priority_qg_call_count = 0


def reset_priority_fakes() -> None:
    global fake_priority_qg_call_count
    fake_priority_qg_call_count = 0


def _generate_priority(
    _state: SessionState,
) -> tuple[list[TopicCandidate], list[QuestionField]]:
    global fake_priority_qg_call_count
    fake_priority_qg_call_count += 1
    topics = [
        TopicCandidate(
            topic="medication",
            relevance_score=0.9,
            is_red_flag=False,
            source="base_reasoning",
        )
    ]
    questions = [
        QuestionField(
            id="meds_q1",
            kind="yes_no",
            prompt="Are you taking any medicines for your symptoms?",
            personalization_note="fake priority for M3",
            collect_target_id="medication",
        )
    ]
    return topics, questions


def priority_questions(state: SessionState) -> Command:
    if not state.pending_questions:
        topics, questions = _generate_priority(state)
        return Command(
            update={
                "prioritised_topics": dump_topic_candidates(topics),
                "pending_questions": dump_question_fields(questions),
                "awaiting_phase": _PHASE,
            },
            goto="priority_questions",
        )

    questions = as_question_fields(state.pending_questions)
    answer = interrupt(
        build_next_step(state, questions, phase=_PHASE).model_dump()
    )
    updates = apply_answers(state, answer, questions)
    return Command(
        update={
            **updates,
            "pending_questions": [],
            "awaiting_phase": None,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="redflag_screening",
    )
