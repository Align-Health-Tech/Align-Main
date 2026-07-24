"""Engine → intelligence boundary (agent_bridge).

Nodes and session_state_mappers call symbols defined here. CI graph tests
patch this module (never Azure). Real Azure only via local prompt smoke
(non-CI). Implementation lives in ``intelligence.agents``.
"""

from __future__ import annotations

from typing import Optional, get_args

from intelligence import agents as _agents
from intelligence.qg_phase_validators import (
    phase_max_questions,
    validate_qg_questions,
)
from intelligence.registry import (
    REDFLAG_TARGETS,
    targets_for_session_phase,
)
from schemas.clinical_ai_io import (
    ClassifierInput,
    ClassifierResult,
    QuestionGenerationInput,
    QuestionGenerationResult,
    ReviewSummaryResult,
    TranslationResult,
)
from schemas.literals import IntakeFactKind
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
) -> list[TopicCandidate]:
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
    """Shared context blob for Classifier / Devise / QG / nurse review.

    Nurse review synthesises the full clinical picture — include encounter
    narratives, body structures, meds, intake facts, and ICE here (not only
    ranking/prefill fields). Other phases ignore unused keys.
    """
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
        # Full synthesis fields (nurse_review; harmless extras for other agents)
        "body_structures": list(state.body_structures),
        "duration": state.duration,
        "persistence": state.persistence,
        "progression": state.progression,
        "onset_circumstance": state.onset_circumstance,
        "character": list(state.character),
        "comorbidities": list(state.comorbidities),
        "encounter_medication": list(state.encounter_medication),
        "intake_facts": list(state.intake_facts),
        "self_management": state.self_management,
        "weight_change": state.weight_change,
        "exacerbating_factors": list(state.exacerbating_factors),
        "mitigating_factors": list(state.mitigating_factors),
        "pregnancy_possible": state.pregnancy_possible,
        "ice_idea": state.ice_idea,
        "ice_concern": state.ice_concern,
        "ice_expectation": state.ice_expectation,
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
    devise: bool = True,
    max_questions: Optional[int] = None,
) -> tuple[list[TopicCandidate], list[QuestionField]]:
    """Pattern C — Devise then Question Generation for one session phase.

    Pass ``devise=False`` for QG-only phases (ICE): skips Devise, uses empty
    topics, still runs eligible lookup + QG + validate.

    Priority and red-flag Devise each make one curated ``web_search`` call.
    Optional and clarification phases remain reasoning-only.
    """
    context = build_agent_context(state)
    if phase in _CLARIFY_PHASES:
        context["conversation"] = conversation_from_state(state)
    if devise:
        topics = run_devise_and_prioritise(phase, context)
    else:
        topics = []
    eligible = _eligible_for_phase(phase, context)
    if phase == "redflag_screening" and topics:
        # QG splits each selected subcategory's clinical_hint into findings.
        context = {
            **context,
            "redflag_finding_hints": _redflag_hints_for_topics(topics),
        }
    # Prefer explicit caller cap; else phase policy (e.g. redflag=9).
    cap = max_questions if max_questions is not None else phase_max_questions(phase)
    result = run_question_generation(
        QuestionGenerationInput(
            prompt_name=phase,
            prioritised_topics=topics,
            eligible_targets=eligible,
            max_questions=cap,
            context=context,
        )
    )
    # Hard truncate — models occasionally ignore max_questions (esp. redflag
    # finding-split). Keep Devise topic order / QG emission order.
    if cap is not None and len(result.questions) > cap:
        result = result.model_copy(update={"questions": result.questions[:cap]})
    validate_qg_questions(phase, result.questions)
    return topics, result.questions


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CLARIFY_PHASES = frozenset(
    {
        "presenting_complaint_clarify",
        "non_localised_clarify",
    }
)

# Derived from IntakeFactKind — kind.lower() is the collect-target / prefill key.
# Apply writes allergy / past_history / family_history / social_history today.
# medication (usual/ongoing) — apply not wired yet; visit meds use
# encounter_medication → known key "medication".
_KNOWN_INTAKE_FACT_TARGETS = frozenset(
    kind.lower() for kind in get_args(IntakeFactKind)
)


def _narrative_text(field: object) -> Optional[str]:
    if isinstance(field, dict):
        text = field.get("text")
        return str(text) if text is not None else None
    return None


def _known_collect_values(state: SessionState) -> dict[str, object]:
    """Plain values QG uses to populate default_value / default_values.

    Keys are registry collect-target ids (1:1 with SessionState field names
    where applicable). Presence of a key means the target is already known.

    briding the actual engine with the interface
    """
    out: dict[str, object] = {}
    onset = _narrative_text(state.onset_circumstance)
    if onset:
        out["onset_circumstance"] = onset
    duration = _narrative_text(state.duration)
    if duration:
        out["duration"] = duration
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
        target = str(fact["kind"]).lower()
        if target not in _KNOWN_INTAKE_FACT_TARGETS:
            continue
        display = fact.get("display")
        text = _narrative_text(display) if display is not None else None
        if not text:
            continue
        # allergy stays a single string for back-compat with QG defaults.
        if target == "allergy":
            if "allergy" not in out:
                out["allergy"] = text
            continue
        bucket = out.setdefault(target, [])
        if isinstance(bucket, list):
            bucket.append(text)
    return out


def _eligible_for_phase(phase: str, context: dict) -> list:
    return targets_for_session_phase(
        phase,
        context.get("patient_sex"),
        context.get("presentation_category"),
    )


def _redflag_hints_for_topics(topics: list[TopicCandidate]) -> list[dict]:
    """``{id, clinical_hint}`` for Devise-selected redflag subcategories."""
    by_sub = {t.subcategory: t.clinical_hint for t in REDFLAG_TARGETS}
    out: list[dict] = []
    for topic in topics:
        hint = by_sub.get(topic.topic)  # type: ignore[arg-type]
        if hint is None:
            continue
        out.append({"id": topic.topic, "clinical_hint": hint})
    return out
