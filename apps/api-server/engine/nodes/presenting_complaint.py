"""presenting_complaint — Pattern B; free_text gate + classifier + clarify loop."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.helpers import agent_bridge
from engine.helpers.apply_answers import apply_answers
from engine.helpers.apply_classifier_result import apply_classifier_result
from engine.helpers.next_step import build_next_step
from engine.helpers.state_codecs import (
    as_question_fields,
    dump_question_fields,
    dump_topic_candidates,
)
from schemas.clinical_ai_io import ClassifierInput
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState

_CLARIFY_PHASE = "presenting_complaint_clarify"


def _free_text_question() -> QuestionField:
    return QuestionField(
        id="pc_chief_complaint",
        kind="free_text",
        prompt="What brings you in today?",
        personalization_note="deterministic",
        collect_target_id="chief_complaint",
    )


def _mark_completed(state: SessionState) -> list[str]:
    completed = list(state.completed_phases)
    if "presenting_complaint" not in completed:
        completed.append("presenting_complaint")
    return completed


def presenting_complaint(state: SessionState) -> Command:
    # --- Stage 1: free-text chief complaint (Option 2) ---
    if state.chief_complaint is None:
        if not state.pending_questions:
            return Command(
                update={
                    "pending_questions": dump_question_fields([_free_text_question()]),
                    "awaiting_phase": "presenting_complaint",
                },
                goto="presenting_complaint",
            )

        questions = as_question_fields(state.pending_questions)
        answer = interrupt(
            build_next_step(
                state, questions, phase="presenting_complaint"
            ).model_dump()
        )
        updates = apply_answers(state, answer, questions)
        return Command(
            update={
                **updates,
                "pending_questions": [],
                "awaiting_phase": None,
            },
            goto="presenting_complaint",
        )

    # --- Stage 2: classify, or clarify then re-enter ---
    if not state.pending_questions:
        result = agent_bridge.run_classifier(
            ClassifierInput(
                prompt_name="presenting_complaint",
                conversation=agent_bridge.conversation_from_state(state),
                context=agent_bridge.build_agent_context(state),
            )
        )
        if result.ready:
            category = result.category or "LOCALISED"
            next_node = (
                "localised_detail"
                if category == "LOCALISED"
                else "non_localised_detail"
            )
            return Command(
                update={
                    **apply_classifier_result(state, result),
                    "completed_phases": _mark_completed(state),
                },
                goto=next_node,
            )

        topics, questions = agent_bridge.devise_then_generate(_CLARIFY_PHASE, state)
        return Command(
            update={
                "prioritised_topics": dump_topic_candidates(topics),
                "pending_questions": dump_question_fields(questions),
                "awaiting_phase": "presenting_complaint",
            },
            goto="presenting_complaint",
        )

    questions = as_question_fields(state.pending_questions)
    answer = interrupt(
        build_next_step(state, questions, phase="presenting_complaint").model_dump()
    )
    updates = apply_answers(state, answer, questions)
    return Command(
        update={
            **updates,
            "pending_questions": [],
            "awaiting_phase": None,
        },
        goto="presenting_complaint",
    )
