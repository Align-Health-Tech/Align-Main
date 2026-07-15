"""Engine → clinical_ai boundary.

Nodes and helpers call symbols defined here. CI graph tests patch this
module (never Azure). Real Azure only via local prompt smoke (non-CI).
"""
from __future__ import annotations

from typing import Optional

from external_systems.clinical_ai import agents as _agents
from external_systems.clinical_ai.registry import get_eligible_targets
from engine.helpers.qg_phase_validators import validate_qg_questions
from schemas.clinical_ai_io import (
    ClassifierInput,
    ClassifierResult,
    QuestionGenerationInput,
    QuestionGenerationResult,
    ReviewSummaryResult,
    TranslationResult,
)
from schemas.collect_targets import SESSION_TO_COLLECT_PHASE
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

__all__ = [
    "build_agent_context",
    "conversation_from_state",
    "devise_then_generate",
    "run_classifier",
    "run_devise_and_prioritise",
    "run_nurse_review_summary_agent",
    "run_question_generation",
    "translate_to_english",
]


def run_classifier(input: ClassifierInput) -> ClassifierResult:
    return _agents.run_classifier(input)


def run_devise_and_prioritise(phase: str, context: dict) -> list[TopicCandidate]:
    return _agents.run_devise_and_prioritise(phase, context)


def run_question_generation(input: QuestionGenerationInput) -> QuestionGenerationResult:
    return _agents.run_question_generation(input)


def run_nurse_review_summary_agent(context: dict) -> ReviewSummaryResult:
    return _agents.run_nurse_review_summary_agent(context)


def translate_to_english(
    source_text: str,
    source_lang: str | None = None,
) -> TranslationResult:
    return _agents.translate_to_english(source_text, source_lang)


def build_agent_context(state: SessionState) -> dict:
    """Shared context blob for Classifier / Devise / QG / nurse review."""
    return {
        "already_known_ids": _already_known_ids(state),
        "patient_sex": state.patient_sex,
        "chief_complaint": state.chief_complaint,
        "presentation_category": state.presentation_category,
        "non_localised_category": state.non_localised_category,
        "non_localised_clarify_rounds": state.non_localised_clarify_rounds,
        "non_localised_category_lean": state.non_localised_category_lean,
        "session_language": state.session_language,
        "raised_flag_topics": list(state.raised_flag_topics),
        "completed_phases": list(state.completed_phases),
        "severity_score": state.severity_score,
        "functional_impact_score": state.functional_impact_score,
    }


def conversation_from_state(state: SessionState) -> list[dict]:
    """Normalize LangGraph messages into [{role, content}] for classifiers."""
    out: list[dict] = []
    for m in state.messages or []:
        if isinstance(m, dict):
            role = m.get("role") or m.get("type") or "user"
            content = m.get("content", "")
        else:
            role = getattr(m, "type", None) or getattr(m, "role", "user")
            content = getattr(m, "content", str(m))
        if role == "human":
            role = "user"
        elif role == "ai":
            role = "assistant"
        out.append({"role": str(role), "content": content})
    return out


def devise_then_generate(
    phase: str,
    state: SessionState,
    *,
    max_questions: Optional[int] = None,
) -> tuple[list[TopicCandidate], list[QuestionField]]:
    """Pattern C — Devise then Question Generation for one session phase."""
    context = build_agent_context(state)
    topics = run_devise_and_prioritise(phase, context)
    eligible = _eligible_for_phase(phase, context)
    result = run_question_generation(
        QuestionGenerationInput(
            prompt_name=phase,
            prioritised_topics=topics,
            eligible_targets=eligible,
            max_questions=max_questions,
            context=context,
        )
    )
    validate_qg_questions(phase, result.questions)
    return topics, result.questions


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _already_known_ids(state: SessionState) -> list[str]:
    known: list[str] = []
    if state.onset_circumstance is not None:
        known.append("onset_circumstance")
    if state.character:
        known.append("symptom_characteristics")
    if state.comorbidities:
        known.append("comorbidities")
    if state.self_management is not None:
        known.append("self_management")
    if state.weight_change is not None:
        known.append("weight_change")
    if state.exacerbating_factors:
        known.append("exacerbating_factors")
    if state.mitigating_factors:
        known.append("mitigating_factors")
    for fact in state.intake_facts or []:
        if isinstance(fact, dict) and fact.get("kind"):
            # soft map — Devise filters by collect target id; kinds are coarse
            kind = str(fact["kind"]).lower()
            if "medication" in kind and "medication" not in known:
                known.append("medication")
            if "allergy" in kind and "allergy" not in known:
                known.append("allergy")
    return known


def _eligible_for_phase(phase: str, context: dict) -> list:
    collect_phase = SESSION_TO_COLLECT_PHASE.get(phase)
    if collect_phase is None:
        return []
    already = set(context.get("already_known_ids") or [])
    return get_eligible_targets(collect_phase, already, context.get("patient_sex"))
