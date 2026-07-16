"""Engine → clinical_ai boundary.

Nodes and helpers call symbols defined here. CI graph tests patch this
module (never Azure). Real Azure only via local prompt smoke (non-CI).
"""
from __future__ import annotations

from typing import Optional

from external_systems.clinical_ai import agents as _agents
from external_systems.clinical_ai.registry import targets_for_session_phase
from engine.helpers.qg_phase_validators import validate_qg_questions
from schemas.clinical_ai_io import (
    ClassifierInput,
    ClassifierResult,
    QuestionGenerationInput,
    QuestionGenerationResult,
    ReviewSummaryResult,
    TranslationResult,
)
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


def run_devise_and_prioritise(
    phase: str,
    context: dict,
    *,
    tool_choice: Optional[str] = None,
) -> list[TopicCandidate]:
    return _agents.run_devise_and_prioritise(
        phase, context, tool_choice=tool_choice
    )


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
        # Target id → known text(s) for QG default_value / default_values.
        # Presence of a target id as a key means already known (prefill-and-confirm).
        "known_collect_values": _known_collect_values(state),
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
    tool_choice: Optional[str] = None,
) -> tuple[list[TopicCandidate], list[QuestionField]]:
    """Pattern C — Devise then Question Generation for one session phase.

    ``tool_choice`` is forwarded to Devise only (default auto). Used by rare
    local plumbing checks — production nodes omit it.
    """
    context = build_agent_context(state)
    topics = run_devise_and_prioritise(phase, context, tool_choice=tool_choice)
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


def _narrative_text(field: object) -> Optional[str]:
    if isinstance(field, dict):
        text = field.get("text")
        return str(text) if text is not None else None
    return None


def _known_collect_values(state: SessionState) -> dict[str, object]:
    """Plain values QG uses to populate default_value / default_values.

    Keys are registry collect-target ids (1:1 with SessionState field names
    where applicable). Presence of a key means the target is already known.
    """
    out: dict[str, object] = {}
    onset = _narrative_text(state.onset_circumstance)
    if onset:
        out["onset_circumstance"] = onset
    if state.character:
        chars = [t for c in state.character if (t := _narrative_text(c))]
        if chars:
            out["character"] = chars
    if state.comorbidities:
        comorb = [t for c in state.comorbidities if (t := _narrative_text(c))]
        if comorb:
            out["comorbidities"] = comorb
    if state.self_management is not None:
        sm = _narrative_text(state.self_management)
        if sm:
            out["self_management"] = sm
    if state.weight_change is not None:
        out["weight_change"] = state.weight_change
    if state.exacerbating_factors:
        ex = [t for c in state.exacerbating_factors if (t := _narrative_text(c))]
        if ex:
            out["exacerbating_factors"] = ex
    if state.mitigating_factors:
        mi = [t for c in state.mitigating_factors if (t := _narrative_text(c))]
        if mi:
            out["mitigating_factors"] = mi
    if state.encounter_medication:
        meds = [t for c in state.encounter_medication if (t := _narrative_text(c))]
        if meds:
            out["medication"] = meds
    if state.pregnancy_possible is not None:
        out["pregnancy"] = state.pregnancy_possible
    for fact in state.intake_facts or []:
        if not isinstance(fact, dict) or not fact.get("kind"):
            continue
        kind = str(fact["kind"]).lower()
        display = fact.get("display")
        text = _narrative_text(display) if display is not None else None
        if not text:
            continue
        # Usual/ongoing allergy only — medication prefill uses encounter_medication.
        if "allergy" in kind and "allergy" not in out:
            out["allergy"] = text
    return out


def _eligible_for_phase(phase: str, context: dict) -> list:
    return targets_for_session_phase(
        phase,
        context.get("patient_sex"),
        context.get("presentation_category"),
    )
