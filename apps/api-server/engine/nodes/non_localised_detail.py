"""non_localised_detail — Pattern B categoriser + deterministic onset/severity."""
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
from schemas.clinical_ai_io import ClassifierResult
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_PHASE = "non_localised_detail"

fake_nl_classifier_call_count = 0
fake_nl_clarify_qg_call_count = 0
_nl_classifier_script: list[ClassifierResult] | None = None


def reset_non_localised_fakes() -> None:
    global fake_nl_classifier_call_count, fake_nl_clarify_qg_call_count
    global _nl_classifier_script
    fake_nl_classifier_call_count = 0
    fake_nl_clarify_qg_call_count = 0
    _nl_classifier_script = None


def set_nl_classifier_script(results: list[ClassifierResult]) -> None:
    global _nl_classifier_script
    _nl_classifier_script = list(results)


def _run_fake_nl_classifier(_state: SessionState) -> ClassifierResult:
    global fake_nl_classifier_call_count
    fake_nl_classifier_call_count += 1
    if _nl_classifier_script is not None:
        idx = min(fake_nl_classifier_call_count - 1, len(_nl_classifier_script) - 1)
        return _nl_classifier_script[idx]
    return ClassifierResult(
        ready=True, category="SYSTEMIC", confidence=0.9, reason="fake default"
    )


def _generate_nl_clarify(_state: SessionState) -> tuple[list[TopicCandidate], list[QuestionField]]:
    global fake_nl_clarify_qg_call_count
    fake_nl_clarify_qg_call_count += 1
    n = fake_nl_clarify_qg_call_count
    topics = [
        TopicCandidate(
            topic="systemic_nature",
            relevance_score=0.8,
            is_red_flag=False,
            source="base_reasoning",
        )
    ]
    questions = [
        QuestionField(
            id=f"nl_clarify_{n}",
            kind="free_text",
            prompt=f"Non-localised clarify {n}: any fever, fatigue, or whole-body symptoms?",
            personalization_note="fake nl clarify",
            collect_target_id="non_localised_clarify",
        )
    ]
    return topics, questions


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
            result = _run_fake_nl_classifier(state)
            if result.ready:
                return Command(
                    update={"non_localised_category": result.category or "SYSTEMIC"},
                    goto="non_localised_detail",
                )
            topics, questions = _generate_nl_clarify(state)
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
