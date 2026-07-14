"""SessionState — LangGraph intake state for one encounter.

Checkpoint storage rule: nested domain shapes are stored as plain dict /
list[dict] (model_dump), never as nested Pydantic instances. Re-hydrate with
Model.model_validate(...) only at engine call sites that need typed objects.
This keeps LangGraph msgpack checkpoints free of unregistered custom types
(QuestionField, TopicCandidate, NarrativeField, BodyStructureState, …).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel

from schemas.jsonb_fields import CodedField, NarrativeField
from schemas.question_fields import Phase

PresentationCategory = Literal["LOCALISED", "NOT_LOCALISED"]
Laterality = Literal["left", "right", "bilateral"]

IntakeFactKind = Literal[
    "ALLERGY", "MEDICATION", "CONDITION", "PROCEDURE", "IMMUNIZATION",
    "FAMILY_HISTORY", "SOCIAL_HISTORY", "VITAL_SIGN", "OTHER_OBSERVATION",
]
IntakeFactSource = Literal["PATIENT_INTAKE", "LILLY_EXTRACTED", "PRACTITIONER_ENTERED"]

# JSON-friendly aliases for checkpointed nested shapes.
JsonDict = dict[str, Any]


class BodyStructureState(BaseModel):
    """Parse helper for one body_structures row — not stored as this type in SessionState."""

    region_detail: Optional[CodedField] = None
    sub_region_detail: Optional[CodedField] = None
    laterality: Optional[Laterality] = None
    severity_score: Optional[int] = None
    radiation_status: Optional[str] = None
    character: list[NarrativeField] = []
    radiation_sites: list[CodedField] = []


class IntakeFactState(BaseModel):
    """Parse helper for one intake_fact_items row — not stored as this type in SessionState."""

    kind: IntakeFactKind
    source: IntakeFactSource
    display: NarrativeField
    fhir_system: Optional[str] = None
    fhir_code: Optional[str] = None
    fhir_display: Optional[str] = None


class SessionState(BaseModel):
    # Identifiers — session_id doubles as encounter_id and the LangGraph thread_id
    session_id: str
    patient_id: str
    organization_id: str
    session_language: str = "en"
    patient_sex: Optional[str] = None

    # Consent is router-level (Consent rows + status). Field kept for optional
    # in-memory bookkeeping if a caller still mirrors acceptances into state.
    consents_accepted: list[str] = []

    # Free-form presenting-complaint conversation (classifier reads this)
    messages: Annotated[list, add_messages] = []

    # Classifier output
    presentation_category: Optional[PresentationCategory] = None
    # Presenting-concerns classifier extras (e.g. localisedAnatomySites) — dict
    presenting_complaint_hint: Optional[JsonDict] = None
    # non_localised_categoriser bucket (set only on NOT_LOCALISED path)
    non_localised_category: Optional[str] = None

    # encounters column mapping — narrative jsonb (dict = NarrativeField.model_dump())
    chief_complaint: Optional[JsonDict] = None
    duration: Optional[JsonDict] = None
    persistence: Optional[JsonDict] = None
    progression: Optional[JsonDict] = None
    onset_circumstance: Optional[JsonDict] = None
    self_management: Optional[JsonDict] = None
    ice_idea: Optional[JsonDict] = None
    ice_concern: Optional[JsonDict] = None
    ice_expectation: Optional[JsonDict] = None
    character: list[JsonDict] = []
    mitigating_factors: list[JsonDict] = []
    exacerbating_factors: list[JsonDict] = []
    comorbidities: list[JsonDict] = []

    # encounters column mapping — plain scalars, no translation needed
    severity_score: Optional[int] = None
    functional_impact_score: Optional[int] = None
    weight_change: Optional[str] = None
    acc_claim_suspected: bool = False
    acc_can_work: Optional[bool] = None

    # Generated directly in English, one line
    encounter_summary: Optional[str] = None

    # body_structures / radiation_sites (dict = BodyStructureState.model_dump())
    body_structures: list[JsonDict] = []

    # Devise output (dict = TopicCandidate.model_dump())
    prioritised_topics: list[JsonDict] = []

    # Topic strings already raised as Flag rows after redflag_screening
    raised_flag_topics: list[str] = []

    # intake_fact_items (dict = IntakeFactState.model_dump())
    intake_facts: list[JsonDict] = []

    # Active interrupt — list[dict] = QuestionField.model_dump(); also Option-2 resume guard
    pending_questions: list[JsonDict] = []
    # localised_detail round-1 (body_diagram) Option-2 arm — None until armed
    pending_diagram_file: Optional[str] = None
    pending_highlighted_regions: Optional[list[str]] = None
    awaiting_phase: Optional[Phase] = None

    completed_phases: list[str] = []
    turn_number: int = 0
    is_session_complete: bool = False
