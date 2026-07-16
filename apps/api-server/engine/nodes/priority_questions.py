"""priority_questions — Pattern C Devise+QG batch."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.helpers import agent_bridge
from engine.helpers.apply import apply_answers
from engine.helpers.completed_phases import with_completed
from engine.helpers.next_step import build_next_step
from engine.helpers.state_codecs import (
    as_question_fields,
    dump_question_fields,
    dump_topic_candidates,
)
from schemas.session_states import SessionState

_PHASE = "priority_questions"


def priority_questions(state: SessionState) -> Command:
    if not state.pending_questions:
        topics, questions = agent_bridge.devise_then_generate(_PHASE, state)
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
