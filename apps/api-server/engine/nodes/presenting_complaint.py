"""presenting_complaint — Pattern B; free_text gate + fake classifier + clarify loop."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.apply_answers import apply_answers
from engine.next_step import build_next_step
from engine.state_codecs import (
    as_question_fields,
    dump_question_fields,
    dump_topic_candidates,
)
from schemas.clinical_ai_io import ClassifierResult
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

fake_classifier_call_count = 0
fake_clarify_qg_call_count = 0
_classifier_script: list[ClassifierResult] | None = None


def reset_presenting_complaint_fakes() -> None:
    global fake_classifier_call_count, fake_clarify_qg_call_count, _classifier_script
    fake_classifier_call_count = 0
    fake_clarify_qg_call_count = 0
    _classifier_script = None


def set_classifier_script(results: list[ClassifierResult]) -> None:
    """Test helper — successive classifier calls return these results in order."""
    global _classifier_script
    _classifier_script = list[ClassifierResult](results)


def _free_text_question() -> QuestionField:
    return QuestionField(
        id="pc_chief_complaint",
        kind="free_text",
        prompt="What brings you in today?",
        personalization_note="deterministic",
        collect_target_id="chief_complaint",
    )


def _run_fake_classifier(state: SessionState) -> ClassifierResult:
    global fake_classifier_call_count
    fake_classifier_call_count += 1
    if _classifier_script is not None:
        idx = min(fake_classifier_call_count - 1, len(_classifier_script) - 1)
        return _classifier_script[idx]

    text = ((state.chief_complaint or {}).get("text") or "").lower()
    if any(w in text for w in ("wrist", "ankle", "knee", "shoulder", "back")):
        return ClassifierResult(
            ready=True, category="LOCALISED", confidence=0.95, reason="body part named"
        )
    if any(w in text for w in ("fever", "tired", "fatigue", "unwell")):
        return ClassifierResult(
            ready=True,
            category="NOT_LOCALISED",
            confidence=0.9,
            reason="systemic wording",
        )
    return ClassifierResult(ready=False, reason="need more detail")


def _generate_clarify(
    _state: SessionState,
) -> tuple[list[TopicCandidate], list[QuestionField]]:
    """Make-only helper — fake Devise+QG for presenting_complaint_clarify.

    Each call gets a distinct question id so multi-round clarify tests can
    prove pending_questions was replaced, not left stale.
    """
    global fake_clarify_qg_call_count
    fake_clarify_qg_call_count += 1
    n = fake_clarify_qg_call_count
    topics = [
        TopicCandidate(
            topic="location_or_nature",
            relevance_score=0.85,
            is_red_flag=False,
            source="base_reasoning",
            rationale="fake clarify",
        )
    ]
    questions = [
        QuestionField(
            id=f"pc_clarify_{n}",
            kind="free_text",
            prompt=f"Clarify round {n}: where exactly, or describe more?",
            personalization_note="fake clarify for M1",
            collect_target_id="chief_complaint_clarify",
        )
    ]
    return topics, questions


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
        result = _run_fake_classifier(state)
        if result.ready:
            category = result.category or "LOCALISED"
            next_node = (
                "localised_detail"
                if category == "LOCALISED"
                else "non_localised_detail"
            )
            return Command(
                update={
                    "presentation_category": category,
                    "completed_phases": _mark_completed(state),
                },
                goto=next_node,
            )

        topics, questions = _generate_clarify(state)
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
