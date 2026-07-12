"""CollectTarget shape, session→collect phase map, RedFlagSubcategory."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

CollectPhase = Literal["priority", "optional"]

# Session / prompt phase → CollectTarget pool (engine + Devise share this).
SESSION_TO_COLLECT_PHASE: dict[str, CollectPhase] = {
    "priority_questions": "priority",
    "optional_questions": "optional",
}

RedFlagSubcategory = Literal[
    "AIRWAY", "BREATHING", "CIRCULATION", "DISABILITY", "TEMPERATURE", "OTHER"
]

FreeTextPolicy = Literal["avoid", "optional_other"]
PatientSexRequirement = Literal["female"]


class CollectTarget(BaseModel):
    id: str
    category: str
    phase: CollectPhase
    clinical_hint: Optional[str] = None
    example_prompt: Optional[str] = None
    suggested_options: Optional[list[str]] = None
    free_text_policy: Optional[FreeTextPolicy] = None
    requires_patient_sex: Optional[PatientSexRequirement] = None
