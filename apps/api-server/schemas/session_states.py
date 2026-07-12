"""SessionState — LangGraph intake state for one encounter."""
from typing import Annotated, Literal, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel

from schemas.jsonb_fields import CodedField, NarrativeField
from schemas.topic_candidates import TopicCandidate

PresentationCategory = Literal["LOCALISED", "NOT_LOCALISED"]
Laterality = Literal["left", "right", "bilateral"]

IntakeFactKind = Literal[
    "ALLERGY", "MEDICATION", "CONDITION", "PROCEDURE", "IMMUNIZATION",
    "FAMILY_HISTORY", "SOCIAL_HISTORY", "VITAL_SIGN", "OTHER_OBSERVATION",
]
IntakeFactSource = Literal["PATIENT_INTAKE", "LILLY_EXTRACTED", "PRACTITIONER_ENTERED"]


class BodyStructureState(BaseModel):
    """Maps to one `body_structures` row (+ its `radiation_sites` children)."""

    region_detail: Optional[CodedField] = None
    sub_region_detail: Optional[CodedField] = None
    laterality: Optional[Laterality] = None
    severity_score: Optional[int] = None
    radiation_status: Optional[str] = None
    character: list[NarrativeField] = []
    radiation_sites: list[CodedField] = []


class IntakeFactState(BaseModel):
    """Maps to one `intake_fact_items` row."""

    kind: IntakeFactKind
    source: IntakeFactSource
    display: NarrativeField
    # Flat FHIR coding — same pattern as `flags` (not CodedField / region_detail).
    fhir_system: Optional[str] = None
    fhir_code: Optional[str] = None
    fhir_display: Optional[str] = None


class SessionState(BaseModel):
    # Identifiers — session_id doubles as encounter_id and the LangGraph thread_id
    session_id: str
    patient_id: str
    organization_id: str
    session_language: str = "en"

    # Registration / consent — gates encounters.status NOT_STARTED -> IN_PROGRESS
    consents_accepted: list[str] = []

    # Free-form presenting-complaint conversation (classifier reads this)
    messages: Annotated[list, add_messages] = []

    # Classifier output
    presentation_category: Optional[PresentationCategory] = None

    # encounters column mapping — narrative jsonb fields
    chief_complaint: Optional[NarrativeField] = None
    duration: Optional[NarrativeField] = None
    persistence: Optional[NarrativeField] = None
    progression: Optional[NarrativeField] = None
    onset_circumstance: Optional[NarrativeField] = None
    self_management: Optional[NarrativeField] = None
    ice_idea: Optional[NarrativeField] = None
    ice_concern: Optional[NarrativeField] = None
    ice_expectation: Optional[NarrativeField] = None
    character: list[NarrativeField] = []
    mitigating_factors: list[NarrativeField] = []
    exacerbating_factors: list[NarrativeField] = []
    comorbidities: list[NarrativeField] = []

    # encounters column mapping — plain scalars, no translation needed
    severity_score: Optional[int] = None
    functional_impact_score: Optional[int] = None
    weight_change: Optional[str] = None
    acc_claim_suspected: bool = False
    acc_can_work: Optional[bool] = None

    # Generated directly in English, one line — no NarrativeField wrapper
    encounter_summary: Optional[str] = None

    # body_structures / radiation_sites mapping
    body_structures: list[BodyStructureState] = []

    # Ranked topics from run_devise_and_prioritise(phase, context)
    prioritised_topics: list[TopicCandidate] = []

    # Topic strings already raised as Flag rows after redflag_screening
    # answers — dedupe when Devise/redflag re-runs adaptively.
    raised_flag_topics: list[str] = []

    # intake_fact_items mapping
    intake_facts: list[IntakeFactState] = []

    # Progress tracking — logged here even for phases that never produce a
    # NextStep (e.g. devise_and_prioritise). See schema/question_fields.py
    # for the patient-facing subset of these values (NextStep.phase).
    completed_phases: list[str] = []
    turn_number: int = 0
    is_session_complete: bool = False