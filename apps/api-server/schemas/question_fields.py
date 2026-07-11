"""
Question-related shapes: what the engine sends the frontend for a batch of
questions, and the top-level NextStep envelope every session endpoint
returns. See apps/api-server/README.md — POST /sessions,
POST /sessions/{id}/respond, and GET /sessions/{id} all return NextStep.
"""
from typing import Literal, Optional

from pydantic import BaseModel

# Which node/phase produced a given NextStep. Distinct from step_type —
# several different phases share the same step_type (e.g. priority_questions,
# redflag_screening, and ice are all "question_batch"). The frontend never
# needs to branch on this; it exists for logging/analytics/dashboard display.
# Mirrors the values pushed into SessionState.completed_phases.
# `devise_and_prioritise` never appears here — it never produces a NextStep
# (no patient-facing interrupt), only ever shows up in completed_phases.
Phase = Literal[
    "consent",
    "presenting_complaint",
    "localised_detail",
    "non_localised_detail",
    "priority_questions",
    "redflag_screening",
    "optional_questions",
    "ice",
    "review",
    "survey",
]


# What the frontend must render for this NextStep.
StepType = Literal["consent", "question_batch", "review", "survey", "complete"]

# What kind of UI control a single question needs.
QuestionKind = Literal["single_choice", "multi_choice", "yes_no", "consent_accept"]


class QuestionOption(BaseModel):
    value: str
    label: str
    en_label: Optional[str] = None  # only set when session_language != "en"


class QuestionField(BaseModel):
    id: str
    kind: QuestionKind
    prompt: str
    en_prompt: Optional[str] = None
    options: Optional[list[QuestionOption]] = None
    allow_other: bool = False
    required: bool = True
    # Which SessionState field this answer ultimately populates — lets the
    # engine route an incoming answer without the frontend knowing anything
    # about internal state shape.
    collect_target_id: Optional[str] = None


class NextStep(BaseModel):
    step_type: StepType
    phase: Phase
    turn_number: int
    questions: Optional[list[QuestionField]] = None
    review_summary: Optional[str] = None