"""non_localised_detail — Pattern B categoriser + deterministic onset/severity."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.helpers import agent_bridge
from engine.helpers.apply_answers import apply_answers
from engine.helpers.completed_phases import with_completed
from engine.helpers.next_step import build_next_step
from engine.helpers.state_codecs import (
    as_question_fields,
    dump_question_fields,
    dump_topic_candidates,
)
from schemas.clinical_ai_io import ClassifierInput
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState

_PHASE = "non_localised_detail"
_CLARIFY_PHASE = "non_localised_clarify"


def _generate_detail_questions(_state: SessionState) -> list[QuestionField]:
    return [
        QuestionField(
            id="nl_onset",
            kind="free_text",
            prompt="How did this start?",
            personalization_note="deterministic",
            collect_target_id="onset_circumstance",
        ),
        QuestionField(
            id="nl_severity",
            kind="single_choice",
            prompt="How severe do you feel overall? (0–10)",
            personalization_note="deterministic",
            collect_target_id="severity_score",
            options=[
                QuestionOption(value=str(i), label=str(i)) for i in range(0, 11)
            ],
        ),
        QuestionField(
            id="nl_functional",
            kind="single_choice",
            prompt="How much is this affecting daily activity? (0–10)",
            personalization_note="deterministic",
            collect_target_id="functional_impact_score",
            options=[
                QuestionOption(value=str(i), label=str(i)) for i in range(0, 11)
            ],
        ),
    ]


def non_localised_detail(state: SessionState) -> Command:
    # --- Stage 1: categoriser / clarify ---
    if state.non_localised_category is None:
        if not state.pending_questions:
            result = agent_bridge.run_classifier(
                ClassifierInput(
                    prompt_name="non_localised_categoriser",
                    conversation=agent_bridge.conversation_from_state(state),
                    context=agent_bridge.build_agent_context(state),
                )
            )
            if result.ready:
                return Command(
                    update={"non_localised_category": result.category or "SYSTEMIC"},
                    goto="non_localised_detail",
                )
            topics, questions = agent_bridge.devise_then_generate(
                _CLARIFY_PHASE, state
            )
            return Command(
                update={
                    "prioritised_topics": dump_topic_candidates(topics),
                    "pending_questions": dump_question_fields(questions),
                    "awaiting_phase": _PHASE,
                },
                goto="non_localised_detail",
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
            },
            goto="non_localised_detail",
        )

    # --- Stage 2: deterministic onset / severity / functional ---
    if not state.pending_questions:
        return Command(
            update={
                "pending_questions": dump_question_fields(
                    _generate_detail_questions(state)
                ),
                "awaiting_phase": _PHASE,
            },
            goto="non_localised_detail",
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
        goto="priority_questions",
    )
