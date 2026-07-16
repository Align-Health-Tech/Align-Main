"""CollectTarget shape and session→collect phase map.

Literal vocabularies (`CollectPhase`, …) live in ``schemas.literals``.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from schemas.literals import (
    CollectPhase,
    FreeTextPolicy,
    PatientSexRequirement,
)

# Session / prompt phase → CollectTarget pool (engine + Devise share this).
SESSION_TO_COLLECT_PHASE: dict[str, CollectPhase] = {
    "priority_questions": "priority",
    "optional_questions": "optional",
}


class CollectTarget(BaseModel):
    id: str
    category: str
    phase: CollectPhase
    clinical_hint: Optional[str] = None
    # Patient-facing phrasing hints — only pregnancy keeps these populated.
    example_prompt: Optional[str] = None
    suggested_options: Optional[list[str]] = None
    free_text_policy: Optional[FreeTextPolicy] = None
    requires_patient_sex: Optional[PatientSexRequirement] = None
    # Pilot locality matrix — which presentation_category may see this target.
    applies_localised: bool = True
    applies_non_localised: bool = True
