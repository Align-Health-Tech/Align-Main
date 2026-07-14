"""QuestionField + NextStep — patient API / frontend response envelope.

`Phase` / `StepType` include `consent` and `survey` even though those are
**not** LangGraph nodes. Routers construct those NextSteps from
`engine/static/deterministic_forms.py`. Every other phase value is produced by a
graph `interrupt()` (or `complete` for terminal).
"""
from typing import Literal, Optional

from pydantic import BaseModel

# Which phase produced a given NextStep. Distinct from step_type —
# several different phases share the same step_type (e.g. priority_questions,
# redflag_screening, and ice are all "question_batch").
# Internal-only graph steps (review nurse summary) never appear here; they
# may still show up in SessionState.completed_phases as plain strings.
Phase = Literal[
    "consent",  # router-constructed (deterministic_forms)
    "presenting_complaint",
    "localised_detail",
    "non_localised_detail",
    "priority_questions",
    "redflag_screening",
    "optional_questions",
    "ice",
    "survey",  # router-constructed (deterministic_forms)
]


# What the frontend must render for this NextStep.
StepType = Literal[
    "consent",  # router-constructed
    "question_batch",  # graph interrupt
    "body_diagram",  # SVG tap — localised_detail round 1
    "survey",  # router-constructed
    "complete",
]

# What kind of UI control a single question needs.
QuestionKind = Literal[
    "single_choice",
    "multi_choice",
    "yes_no",
    "consent_accept",
    "free_text",
]


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
    # Why these options/phrasing fit *this* patient — required so QG cannot
    # blindly copy registry suggested_options. Frontend may ignore; logging/HIL use it.
    personalization_note: str


class NextStep(BaseModel):
    step_type: StepType
    phase: Phase
    turn_number: int
    questions: Optional[list[QuestionField]] = None
    # body_diagram only — which SVG sheet + orange-hint region ids
    diagram_file: Optional[str] = None
    highlighted_region_ids: Optional[list[str]] = None
