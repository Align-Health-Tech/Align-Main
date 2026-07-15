"""NarrativeField and CodedField — shared jsonb column shapes."""
from typing import Literal, Optional

from pydantic import BaseModel

# Where NarrativeField.text came from.
# - option: patient tapped a pre-generated choice
# - free_text: patient typed (incl. "Other" escape)
# - ai_summary: LLM-authored synthesis (e.g. chief_complaint at classifier
#   ready:true) — not patient words; dashboard may label accordingly
AnswerSource = Literal["option", "free_text", "ai_summary"]


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
    # Optional for fields that historically omit source (e.g. some ICE /
    # intake_fact_items.display). Prefer setting source when known.
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