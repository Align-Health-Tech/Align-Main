"""non_localised_detail — Pattern B categoriser + deterministic onset/severity."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.helpers import agent_bridge
from engine.helpers.apply import apply_answers
from engine.helpers.apply_classifier_result import apply_classifier_result
from engine.helpers.completed_phases import with_completed
from engine.helpers.next_step import build_next_step
from engine.helpers.state_codecs import (
    as_question_fields,
    dump_question_fields,
    dump_topic_candidates,
)
from engine.static.onset_timing import ONSET_TIMING_OPTIONS
from schemas.clinical_ai_io import ClassifierInput, ClassifierResult
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState

_PHASE = "non_localised_detail"
_CLARIFY_PHASE = "non_localised_clarify"
_CATEGORISER = "non_localised_categoriser"
_MAX_CLARIFY_ROUNDS = 3
# Last-resort force-commit when no lean was stored from ready:false results.
_FORCE_COMMIT_DEFAULT = "SYSTEMIC"
_NL_BUCKETS = frozenset(
    {
        "SYSTEMIC",
        "GASTROINTESTINAL",
        "NEUROLOGICAL",
        "ALLERGIC_IMMUNE",
        "DISTRIBUTED_MSK",
        "DERMATOLOGICAL",
    }
)


def _generate_detail_questions(_state: SessionState) -> list[QuestionField]:
    return [
        QuestionField(
            id="nl_onset",
            kind="single_choice",
            prompt="When did this start?",
            personalization_note="deterministic",
            collect_target_id="onset_circumstance",
            options=list(ONSET_TIMING_OPTIONS),
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


def _lean_from_result(result: ClassifierResult) -> str | None:
    """Best-fit bucket when ready:false — model should still set category."""
    cat = result.category
    if cat is None:
        return None
    if cat in _NL_BUCKETS:
        return cat
    return None


def _force_commit_bucket(state: SessionState) -> str:
    lean = state.non_localised_category_lean
    if lean is not None and lean in _NL_BUCKETS:
        return lean
    return _FORCE_COMMIT_DEFAULT


def non_localised_detail(state: SessionState) -> Command:
    # --- Stage 1: categoriser / clarify ---
    if state.non_localised_category is None:
        if not state.pending_questions:
            # Hard stop: after 3 enqueued clarify rounds, never call classifier
            # again — commit from stored lean (or SYSTEMIC default).
            if state.non_localised_clarify_rounds >= _MAX_CLARIFY_ROUNDS:
                return Command(
                    update={
                        "non_localised_category": _force_commit_bucket(state),
                    },
                    goto="non_localised_detail",
                )

            result = agent_bridge.run_classifier(
                ClassifierInput(
                    prompt_name=_CATEGORISER,
                    conversation=agent_bridge.conversation_from_state(state),
                    context=agent_bridge.build_agent_context(state),
                )
            )
            if result.ready:
                return Command(
                    update=apply_classifier_result(
                        state, result, prompt_name=_CATEGORISER
                    ),
                    goto="non_localised_detail",
                )

            lean = _lean_from_result(result)
            topics, questions = agent_bridge.devise_then_generate(
                _CLARIFY_PHASE, state
            )
            return Command(
                update={
                    "prioritised_topics": dump_topic_candidates(topics),
                    "pending_questions": dump_question_fields(questions),
                    "awaiting_phase": _PHASE,
                    # Increment only when a new clarify batch is enqueued
                    # (not on the Option-2 interrupt re-entry).
                    "non_localised_clarify_rounds": (
                        state.non_localised_clarify_rounds + 1
                    ),
                    **(
                        {"non_localised_category_lean": lean}
                        if lean is not None
                        else {}
                    ),
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
