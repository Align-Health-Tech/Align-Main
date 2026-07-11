"""
Reusable jsonb shapes.
Every jsonb-shaped column in this schema is one of these two patterns —
don't invent a third.
"""
from typing import Literal, Optional

from pydantic import BaseModel

# Whether an answer came from a pre-generated option or free-text "Other".
AnswerSource = Literal["option", "free_text"]


class NarrativeField(BaseModel):
    """Free text, or an option pick with no clinical code attached.

    Used by: encounters.chief_complaint / duration / persistence /
    progression / onset_circumstance / self_management / ice_idea /
    ice_concern / ice_expectation; each element of encounters.character /
    mitigating_factors / exacerbating_factors / comorbidities; and
    intake_fact_items.display.
    """

    text: str
    en_text: Optional[str] = None
    # None for fields that are never option-driven (chief_complaint,
    # intake_fact_items.display) — always free-form patient input, so
    # there's no option/free_text distinction to record there.
    source: Optional[AnswerSource] = None


class CodedField(BaseModel):
    """Static, code-backed lookup — never LLM-generated.

    Used by: body_structures.region_detail / sub_region_detail,
    radiation_sites.region_detail. Resolved from a fixed diagram region ID
    via an app-side lookup (or seed table), not translated patient input.
    """

    layman_term: str
    anatomical_term: str
    fhir_system: str
    fhir_code: str