"""ice — Pattern C minus devise; free-text idea / concern / expectation."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.helpers import agent_bridge
from engine.helpers.apply_answers import apply_answers
from engine.helpers.completed_phases import with_completed
from engine.helpers.next_step import build_next_step
from engine.helpers.state_codecs import as_question_fields, dump_question_fields
from schemas.clinical_ai_io import QuestionGenerationInput
from schemas.session_states import SessionState

_PHASE = "ice"


def ice(state: SessionState) -> Command:
    if not state.pending_questions:
        result = agent_bridge.run_question_generation(
            QuestionGenerationInput(
                prompt_name=_PHASE,
                prioritised_topics=[],
                eligible_targets=[],
                context=agent_bridge.build_agent_context(state),
            )
        )
        return Command(
            update={
                "pending_questions": dump_question_fields(result.questions),
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
