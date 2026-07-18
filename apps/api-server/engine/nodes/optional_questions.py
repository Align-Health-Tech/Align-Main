"""optional_questions — Pattern C skippable Devise+QG batch."""
from __future__ import annotations

from typing import Any

from langgraph.types import Command, interrupt

from engine import agent_bridge
from engine.session_state_mappers import map_patient_answers
from engine.helpers.completed_phases import with_completed
from engine.helpers.next_step import build_next_step
from engine.helpers.state_codecs import (
    as_question_fields,
    dump_question_fields,
    dump_topic_candidates,
)
from schemas.session_states import SessionState

_PHASE = "optional_questions"


def optional_questions(state: SessionState) -> Command:
    if not state.pending_questions:
        topics, questions = agent_bridge.devise_then_generate(
            _PHASE,
            state,
            max_questions=4,
        )
        if not questions:
            return Command(
                update={
                    "prioritised_topics": dump_topic_candidates(topics),
                    "pending_questions": [],
                    "awaiting_phase": None,
                    "completed_phases": with_completed(state, _PHASE),
                },
                goto="ice",
            )
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

    updates = map_patient_answers(state, answer, questions)
    return Command(
        update={
            **updates,
            "pending_questions": [],
            "awaiting_phase": None,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="ice",
    )
