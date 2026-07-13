"""redflag_screening — Pattern C; yes answers append raised_flag_topics."""
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

_PHASE = "redflag_screening"

fake_redflag_qg_call_count = 0


def reset_redflag_fakes() -> None:
    global fake_redflag_qg_call_count
    fake_redflag_qg_call_count = 0


def _generate_redflag(
    _state: SessionState,
) -> tuple[list[TopicCandidate], list[QuestionField]]:
    global fake_redflag_qg_call_count
    fake_redflag_qg_call_count += 1
    topics = [
        TopicCandidate(
            topic="chest_pain",
            relevance_score=0.95,
            is_red_flag=True,
            source="base_reasoning",
        ),
        TopicCandidate(
            topic="neurological_deficit",
            relevance_score=0.7,
            is_red_flag=True,
            source="base_reasoning",
        ),
    ]
    questions = [
        QuestionField(
            id="rf_chest_pain",
            kind="yes_no",
            prompt="Do you have chest pain or pressure?",
            personalization_note="fake redflag",
            collect_target_id="chest_pain",
        ),
        QuestionField(
            id="rf_neuro",
            kind="yes_no",
            prompt="Any sudden weakness, numbness, or vision loss?",
            personalization_note="fake redflag",
            collect_target_id="neurological_deficit",
        ),
    ]
    return topics, questions


def redflag_screening(state: SessionState) -> Command:
    if not state.pending_questions:
        topics, questions = _generate_redflag(state)
        return Command(
            update={
                "prioritised_topics": dump_topic_candidates(topics),
                "pending_questions": dump_question_fields(questions),
                "awaiting_phase": _PHASE,
            },
            goto="redflag_screening",
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
        goto="optional_questions",
    )
