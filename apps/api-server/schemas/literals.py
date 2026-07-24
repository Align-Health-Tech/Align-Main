"""Shared Literal / enum-like vocabularies for schemas and DB models.

Single source of truth — do not redefine these aliases elsewhere.
Import from ``schemas.literals`` only.

Convention: every ``Literal`` member on its own line (even for 1–2 values).
"""
from __future__ import annotations

from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Encounter routing & status
# ---------------------------------------------------------------------------

# LOCALISED → body-diagram path; NOT_LOCALISED → systemic / non-site path.
PresentationCategory = Literal[
    "LOCALISED",
    "NOT_LOCALISED",
]

EncounterStatus = Literal[
    "NOT_STARTED",
    "IN_PROGRESS",
    "AWAITING_REVIEW",
    "COMPLETED",
]

# ---------------------------------------------------------------------------
# Anatomy / body diagram
# ---------------------------------------------------------------------------

# Stored on body_structures.laterality (and SessionState body rows).
Laterality = Literal[
    "left",
    "right",
    "bilateral",
]

# Classifier / catalogue controlled vocab for site side (broader than Laterality).
Side = Literal[
    "left",
    "right",
    "both",
    "midline",
    "unknown",
]

# Classifier / catalogue controlled vocab for diagram surface.
Surface = Literal[
    "front",
    "back",
    "inner",
    "outer",
    "unknown",
]

# Which sex-specific diagram sheet to use; None = unisex sheet.
SexVariantValue = Literal[
    "male",
    "female",
]
SexVariant = Optional[SexVariantValue]

# ---------------------------------------------------------------------------
# Intake facts (intake_fact_items) — patient-scoped persistent facts.
# MEDICATION here = usual/ongoing meds (FHIR MedicationStatement).
# Visit-symptom meds live on Encounter.encounter_medication, not this table.
# ---------------------------------------------------------------------------
IntakeFactKind = Literal[
    "ALLERGY",
    "MEDICATION",
    "PAST_HISTORY",
    "FAMILY_HISTORY",
    "SOCIAL_HISTORY",
]

IntakeFactSource = Literal[
    "PATIENT_INTAKE",
    "LILLY_EXTRACTED",
    "PRACTITIONER_ENTERED",
]

# ---------------------------------------------------------------------------
# Flags (red-flag / safety rows)
# ---------------------------------------------------------------------------

FlagStatus = Literal[
    "ACTIVE",
    "INACTIVE",
    "ENTERED_IN_ERROR",
]

# Lilly red-flag screening subcategories (Devise pool for redflag_screening).
RedFlagSubcategory = Literal[
    "AIRWAY",
    "BREATHING",
    "CIRCULATION",
    "DISABILITY",
    "TEMPERATURE",
    "OTHER",
]

# ---------------------------------------------------------------------------
# Narrative jsonb (NarrativeField.source)
# ---------------------------------------------------------------------------

# Where NarrativeField.text came from.
# - option: patient tapped a pre-generated choice
# - free_text: patient typed (incl. "Other" escape)
# - ai_summary: LLM-authored synthesis (e.g. chief_complaint at classifier ready)
AnswerSource = Literal[
    "option",
    "free_text",
    "ai_summary",
]

# ---------------------------------------------------------------------------
# Patient UI envelope (QuestionField / NextStep)
# ---------------------------------------------------------------------------

# Which phase produced a NextStep. Distinct from StepType — several phases
# share the same step_type (e.g. priority / redflag / ice → question_batch).
# consent / survey are router-constructed (deterministic_forms), not graph nodes.
# review / complete are graph nodes but not patient NextStep phases (no interrupt).
Phase = Literal[
    "consent",
    "presenting_complaint",
    "localised_detail",
    "non_localised_detail",
    "priority_questions",
    "redflag_screening",
    "optional_questions",
    "ice",
    "survey",
]

# What the frontend must render for this NextStep.
StepType = Literal[
    "consent",
    "question_batch",
    "body_diagram",
    "survey",
    "complete",
]

# UI control kind for one QuestionField.
QuestionKind = Literal[
    "single_choice",
    "multi_choice",
    "yes_no",
    "consent_accept",
    "free_text",
]

# ---------------------------------------------------------------------------
# Collect-target planner (priority / optional Devise+QG)
# ---------------------------------------------------------------------------

# Which CollectTarget pool a session phase draws from.
CollectPhase = Literal[
    "priority",
    "optional",
]

# How free-text "Other" is allowed on a collect target's options.
FreeTextPolicy = Literal[
    "avoid",
    "optional_other",
]

# Sex gate on CollectTarget.requires_patient_sex (pregnancy).
PatientSexRequirement = Literal[
    "female",
]

# ---------------------------------------------------------------------------
# Devise topic ranking
# ---------------------------------------------------------------------------

TopicSource = Literal[
    "web_search",
    "base_reasoning",
]

# ---------------------------------------------------------------------------
# Identity / org / audit (DB column vocabularies)
# ---------------------------------------------------------------------------

PatientKind = Literal[
    "GUEST",
    "REGISTERED",
    "DEMO",
]

PractitionerRole = Literal[
    "DOCTOR",
    "NURSE",
    "GP",
    "PHYSICIAN",
    "RECEPTIONIST",
]

# Organization segment — also the only real Postgres ENUM in the schema.
SegmentType = Literal[
    "PHYSIO",
    "URGENT_CARE",
    "GP",
]

ActorKind = Literal[
    "PATIENT",
    "PRACTITIONER",
    "AI",
    "SYSTEM",
]

AiOperation = Literal[
    "INTAKE_CLASSIFY",
    "REDFLAG_DETECT",
    "PRECONSULT_SUMMARY",
    "QUESTION_GENERATION",
]
