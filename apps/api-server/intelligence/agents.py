"""run_* agent entrypoints (Classifier, Devise, QG, nurse review, translation)."""

from __future__ import annotations

import json
import re
from typing import Optional

from pydantic import BaseModel, Field

from intelligence.llm_client import run_agent, run_agent_with_tools
from intelligence.registry import (
    REDFLAG_TARGETS,
    normalize_redflag_subcategory,
    targets_for_session_phase,
)
from intelligence.tools import web_search
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
# Devise & Prioritise — private parse types stay here
# ---------------------------------------------------------------------------

# Fields Devise may see — never example_prompt / suggested_options (QG-only).
_DEVISE_TARGET_FIELDS = {"id", "category", "clinical_hint"}
_DEVISE_REDFLAG_FIELDS = {"subcategory", "clinical_hint"}


class _DeviseCandidate(BaseModel):
    topic: str
    relevance_score: float = Field(ge=0, le=1)
    source: TopicSource = "base_reasoning"
    rationale: Optional[str] = None
    evidence_urls: list[str] = Field(default_factory=list)


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
        return [t.model_dump(include=_DEVISE_REDFLAG_FIELDS) for t in REDFLAG_TARGETS]

    return []


def run_devise_and_prioritise(
    phase: str,
    context: dict,
) -> list[TopicCandidate]:
    """Rank topics from model reasoning; red-flag status is stamped in code."""
    candidate_pool = _get_candidate_pool(phase, context)
    payload = {
        "context": context,
        "candidate_pool": candidate_pool,
    }
    tool_trace: list[dict] = []
    if phase in _EVIDENCE_ENABLED_PHASES:
        raw = run_agent_with_tools(
            "devise_and_prioritise",
            phase,
            payload,
            _DeviseTopicsResult,
            tools=[web_search],
            tool_choice="required",
            tool_trace=tool_trace,
            tool_default_args={
                "web_search": {
                    "query": _evidence_fallback_query(context),
                }
            },
        )
    else:
        raw = run_agent(
            "devise_and_prioritise",
            phase,
            payload,
            _DeviseTopicsResult,
        )

    successful_urls = _successful_evidence_urls(tool_trace)
    is_red_flag = phase == "redflag_screening"
    allowed_topics = (
        {row["id"] for row in candidate_pool}
        if phase in SESSION_TO_COLLECT_PHASE
        else None
    )
    out: list[TopicCandidate] = []
    for c in raw.candidates:
        if allowed_topics is not None and c.topic not in allowed_topics:
            continue
        if is_red_flag and c.relevance_score < 0.65:
            continue
        topic = c.topic
        if is_red_flag:
            topic = normalize_redflag_subcategory(c.topic)
        evidence_urls = _validated_candidate_urls(
            getattr(c, "evidence_urls", []),
            successful_urls,
        )
        out.append(
            TopicCandidate(
                topic=topic,
                relevance_score=c.relevance_score,
                is_red_flag=is_red_flag,
                source="web_search" if evidence_urls else "base_reasoning",
                rationale=c.rationale,
                evidence_urls=evidence_urls,
            )
        )
        if is_red_flag and len(out) == 3:
            break
    return out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_EVIDENCE_ENABLED_PHASES = frozenset(
    {
        "priority_questions",
        "redflag_screening",
    }
)
_QUERY_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def _evidence_fallback_query(context: dict) -> str:
    """Build a concise query only when the model leaves its tool arg blank."""
    chief_complaint = context.get("chief_complaint")
    if isinstance(chief_complaint, dict):
        text = str(chief_complaint.get("text") or "")
    else:
        text = str(chief_complaint or "")

    words = [match.group(0) for match in _QUERY_WORD_PATTERN.finditer(text)]
    if len(words) < 3:
        words.extend(["clinical", "warning", "signs"])
    return " ".join(words[:12])


def _successful_evidence_urls(tool_trace: list[dict]) -> list[str]:
    """Read successful URLs from this invocation's traced tool result."""
    for trace in tool_trace:
        if trace.get("name") != "web_search":
            continue
        result = trace.get("result")
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                return []
        if not isinstance(result, dict):
            return []
        sources = result.get("successful_sources")
        if not isinstance(sources, list):
            return []
        urls: list[str] = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            url = source.get("url")
            if isinstance(url, str) and url not in urls:
                urls.append(url)
        return urls[:3]
    return []


def _validated_candidate_urls(
    candidate_urls: list[str],
    successful_urls: list[str],
) -> list[str]:
    requested = set(candidate_urls or [])
    return [url for url in successful_urls if url in requested][:3]
