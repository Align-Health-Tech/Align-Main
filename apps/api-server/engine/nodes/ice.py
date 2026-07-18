"""ice — Pattern C with Devise skipped; multi_choice chips + Other free text."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine import agent_bridge
from engine.session_state_mappers import map_patient_answers
from engine.helpers.completed_phases import with_completed
from engine.helpers.next_step import build_next_step
from engine.helpers.state_codecs import as_question_fields, dump_question_fields
from schemas.session_states import SessionState

_PHASE = "ice"


def ice(state: SessionState) -> Command:
    if not state.pending_questions:
        _topics, questions = agent_bridge.devise_then_generate(
            _PHASE, state, devise=False
        )
        return Command(
            update={
                "pending_questions": dump_question_fields(questions),
                "awaiting_phase": _PHASE,
            },
            goto="ice",
        )

    questions = as_question_fields(state.pending_questions)
    answer = interrupt(build_next_step(state, questions, phase=_PHASE).model_dump())
    updates = map_patient_answers(state, answer, questions)
    return Command(
        update={
            **updates,
            "pending_questions": [],
            "awaiting_phase": None,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="review",
    )
