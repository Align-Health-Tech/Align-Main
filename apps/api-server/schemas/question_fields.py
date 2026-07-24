"""QuestionField + NextStep — patient API / frontend response envelope.

`Phase` / `StepType` include `consent` and `survey` even though those are
**not** LangGraph nodes. Routers construct those NextSteps from
`forms/`. Every other phase value is produced by a
graph `interrupt()` (or `complete` for terminal).

Literal vocabularies live in ``schemas.literals``.
"""
from typing import Optional

from pydantic import BaseModel

from schemas.literals import Phase, QuestionKind, StepType


class QuestionOption(BaseModel):
    value: str
    label: str
    en_label: Optional[str] = None  # only set when session_language != "en"


class QuestionField(BaseModel):
    id: str
    kind: QuestionKind
    prompt: str
    en_prompt: Optional[str] = None  # only set when session_language != "en"
    options: Optional[list[QuestionOption]] = None
    required: bool = True
    # Prefill for single-value kinds (single_choice / yes_no / free_text).
    # Patient may accept as-is or edit before submit.
    default_value: Optional[str] = None
    # Prefill for multi_choice — list of pre-selected option values.
    # Kept separate from default_value: kind already discriminates shape.
    default_values: Optional[list[str]] = None
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
