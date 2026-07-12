"""Input/Result models for Classifier, QG, review summary, and translation."""
from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from schemas.collect_targets import CollectTarget
from schemas.question_fields import QuestionField
from schemas.topic_candidates import TopicCandidate


# --- Classifier ---


class ClassifierInput(BaseModel):
    conversation: list  # [{role, content}]
    context: dict
    prompt_name: str  # "presenting_complaint" | "non_localised_categoriser"


class ClassifierResult(BaseModel):
    ready: bool
    category: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    reason: Optional[str] = None
    extra: dict = Field(default_factory=dict)


# --- Question Generation ---


class QuestionGenerationInput(BaseModel):
    prompt_name: str
    prioritised_topics: list[TopicCandidate] = Field(default_factory=list)
    eligible_targets: list[CollectTarget] = Field(default_factory=list)
    max_questions: Optional[int] = None
    context: dict = Field(default_factory=dict)


class QuestionGenerationResult(BaseModel):
    reason: str
    questions: list[QuestionField]


# --- Helpers (nurse review + translation) ---


class ReviewSummaryResult(BaseModel):
    """Legacy prompt JSON key is oneLineSummary; Python attr is summary."""

    model_config = ConfigDict(populate_by_name=True)

    summary: str = Field(
        validation_alias=AliasChoices("oneLineSummary", "summary"),
        serialization_alias="oneLineSummary",
        description="Concise English nurse/clinician review summary",
    )


class TranslationResult(BaseModel):
    en_text: str = Field(description="English translation of the patient text")
    detected_lang: Optional[str] = Field(
        default=None,
        description="BCP-47 / ISO language code if detected (e.g. mi, zh, ko)",
    )
