"""run_* agent entrypoints (Classifier, Devise, QG, nurse review, translation)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from external_systems.clinical_ai.llm_client import run_agent, run_agent_with_tools
from external_systems.clinical_ai.registry import (
    REDFLAG_SUBCATEGORIES,
    targets_for_session_phase,
)
from external_systems.clinical_ai.tools import web_search
from schemas.collect_targets import SESSION_TO_COLLECT_PHASE
from schemas.clinical_ai_io import (
    ClassifierInput,
    ClassifierResult,
    QuestionGenerationInput,
    QuestionGenerationResult,
    ReviewSummaryResult,
    TranslationResult,
)
from schemas.literals import TopicSource
from schemas.topic_candidates import TopicCandidate

__all__ = [
    "run_classifier",
    "run_question_generation",
    "run_nurse_review_summary_agent",
    "translate_to_english",
    "run_devise_and_prioritise",
]


def run_classifier(input: ClassifierInput) -> ClassifierResult:
    """LOCALISED vs NOT_LOCALISED (or non-localised buckets). ready=False → engine clarify."""
    result = run_agent(
        "classifier",
        input.prompt_name,
        {"conversation": input.conversation, "context": input.context},
        ClassifierResult,
    )
    if input.prompt_name == "non_localised_categoriser":
        return _null_pc_only_fields(result)
    return result


def _null_pc_only_fields(result: ClassifierResult) -> ClassifierResult:
    """NL categoriser must not carry PC-shaped fields."""
    if (
        result.chief_complaint_summary is None
        and result.localised_anatomy_sites is None
        and result.encounter_intake_supplement is None
    ):
        return result
    return result.model_copy(
        update={
            "chief_complaint_summary": None,
            "localised_anatomy_sites": None,
            "encounter_intake_supplement": None,
        }
    )


def run_question_generation(input: QuestionGenerationInput) -> QuestionGenerationResult:
    """Turn prioritised topics into patient-facing QuestionFields."""
    return run_agent(
        "question_generation",
        input.prompt_name,
        {
            "prioritised_topics": [t.model_dump() for t in input.prioritised_topics],
            # QG needs phrasing metadata; Devise pool deliberately excludes these.
            "eligible_targets": [t.model_dump() for t in input.eligible_targets],
            "max_questions": input.max_questions,
            "context": input.context,
        },
        QuestionGenerationResult,
    )


def run_nurse_review_summary_agent(context: dict) -> ReviewSummaryResult:
    return run_agent(
        "nurse_review",
        "summary",
        {"context": context},
        ReviewSummaryResult,
    )


def translate_to_english(
    source_text: str,
    source_lang: str | None = None,
) -> TranslationResult:
    return run_agent(
        "translation",
        "to_english",
        {"source_text": source_text, "source_lang": source_lang},
        TranslationResult,
    )


# ---------------------------------------------------------------------------
# Devise & Prioritise (tools path) — private parse types stay here
# ---------------------------------------------------------------------------

# Fields Devise may see — never example_prompt / suggested_options (QG-only).
_DEVISE_TARGET_FIELDS = {"id", "category", "clinical_hint"}


class _DeviseCandidate(BaseModel):
    topic: str
    relevance_score: float = Field(ge=0, le=1)
    source: TopicSource = "base_reasoning"
    rationale: Optional[str] = None


class _DeviseTopicsResult(BaseModel):
    candidates: list[_DeviseCandidate]


def _get_candidate_pool(phase: str, context: dict) -> list[dict]:
    """Devise pool: collect targets (id/category/hint) or redflag subcategories."""
    if phase in SESSION_TO_COLLECT_PHASE:
        targets = targets_for_session_phase(
            phase,
            context.get("patient_sex"),
            context.get("presentation_category"),
        )
        return [t.model_dump(include=_DEVISE_TARGET_FIELDS) for t in targets]

    if phase == "redflag_screening":
        return [{"subcategory": s} for s in REDFLAG_SUBCATEGORIES]

    return []


def run_devise_and_prioritise(
    phase: str,
    context: dict,
    *,
    tool_choice: Optional[str] = None,
) -> list[TopicCandidate]:
    """Rank topics for this phase. Uses web_search; is_red_flag set for redflag_screening.

    ``tool_choice`` defaults to model auto (None). Pass ``\"web_search\"`` only
    for rare plumbing checks — not habitual production or smoke paths.
    """
    raw = run_agent_with_tools(
        "devise_and_prioritise",
        phase,
        {"context": context, "candidate_pool": _get_candidate_pool(phase, context)},
        _DeviseTopicsResult,
        tools=[web_search],
        tool_choice=tool_choice,
    )
    is_red_flag = phase == "redflag_screening"
    return [
        TopicCandidate(
            topic=c.topic,
            relevance_score=c.relevance_score,
            is_red_flag=is_red_flag,
            source=c.source,
            rationale=c.rationale,
        )
        for c in raw.candidates
    ]
