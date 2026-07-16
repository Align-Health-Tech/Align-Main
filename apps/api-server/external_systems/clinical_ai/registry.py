"""Collect-target catalogs for Devise/QG ranking + eligibility filters.

This module is the static *registry* of what can be asked in priority /
optional / redflag pools — not a DI container. It owns:

- ``PRIORITY_TARGETS`` / ``OPTIONAL_TARGETS`` — collect targets with clinical
  hints, sex/locality gates, free-text policy
- ``REDFLAG_SUBCATEGORIES`` — ABCDE-style red-flag topic labels for Devise
- ``get_eligible_targets`` — filter a collect phase by sex + presentation
- ``targets_for_session_phase`` — map graph/QG phase names
  (e.g. ``priority_questions``) onto those filtered targets

Already-known status is *not* filtered here; that flows via
``known_collect_values`` on agent context (prefill-and-confirm).
"""
from typing import Optional

from schemas.collect_targets import SESSION_TO_COLLECT_PHASE, CollectTarget
from schemas.literals import CollectPhase, RedFlagSubcategory


PRIORITY_TARGETS: list[CollectTarget] = [
    CollectTarget(
        id="medication",
        category="MEDICATION_MANAGEMENT",
        phase="priority",
        # Visit-scoped → Encounter.encounter_medication (not intake_fact_items).
        clinical_hint=(
            "Meds for this visit's symptoms only (OTC or prescribed now). "
            "Not usual/ongoing medicines."
        ),
        free_text_policy="optional_other",
        applies_localised=True,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="character",
        category="SYMPTOM_CHARACTERISTIC",
        phase="priority",
        clinical_hint="Frequency, persistence, pain quality, tenderness.",
        free_text_policy="optional_other",
        applies_localised=True,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="onset_circumstance",
        category="ONSET_CIRCUMSTANCE",
        phase="priority",
        clinical_hint="How the problem started — mechanism (fell, twisted, bumped).",
        free_text_policy="optional_other",
        applies_localised=True,
        applies_non_localised=False,
    ),
    CollectTarget(
        id="allergy",
        category="ALLERGY",
        phase="priority",
        clinical_hint="Allergy types or named allergens relevant to this visit.",
        free_text_policy="optional_other",
        applies_localised=True,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="comorbidities",
        category="COMORBIDITIES",
        phase="priority",
        clinical_hint=(
            "Long-term conditions under treatment. Prefer context-relevant "
            "options; always include 'None of these'; never 'Other'."
        ),
        free_text_policy="avoid",
        applies_localised=True,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="pregnancy",
        category="PREGNANCY",
        phase="priority",
        # Maps to Encounter.pregnancy_possible (bool), not intake_fact_items.
        clinical_hint="Whether pregnancy is possible.",
        example_prompt="Is there any chance you could be pregnant?",
        suggested_options=["No", "Yes"],
        requires_patient_sex="female",
        applies_localised=True,
        applies_non_localised=True,
    ),
]

OPTIONAL_TARGETS: list[CollectTarget] = [
    CollectTarget(
        id="past_history",
        category="PAST_HISTORY",
        phase="optional",
        # Apply split (when optional_questions is ported): each selected option
        # becomes an intake_fact_items row on the patient —
        #   "Major surgery" → kind=PROCEDURE
        #   "Hospital stay for serious illness" / "Cancer treatment in the past"
        #   / "Other" (+ free text) → kind=CONDITION
        # Do not dump the whole multi_choice into a single CONDITION row.
        clinical_hint=(
            "Past surgeries, hospital stays, or serious prior illness. "
            "'Major surgery' vs other serious conditions when distinguishing."
        ),
        free_text_policy="optional_other",
        applies_localised=True,
        applies_non_localised=False,
    ),
    CollectTarget(
        id="family_history",
        category="FAMILY_HISTORY",
        phase="optional",
        clinical_hint="Immediate-family major ongoing conditions.",
        free_text_policy="optional_other",
        applies_localised=False,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="self_management",
        category="SELF_MANAGEMENT",
        phase="optional",
        clinical_hint="What the patient already tried for this problem before presenting.",
        free_text_policy="optional_other",
        applies_localised=True,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="weight_change",
        category="WEIGHT_CHANGE",
        phase="optional",
        clinical_hint="Unintentional weight change.",
        applies_localised=False,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="exacerbating_factors",
        category="EXACERBATING_FACTORS",
        phase="optional",
        clinical_hint="What makes symptoms worse.",
        applies_localised=True,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="mitigating_factors",
        category="MITIGATING_FACTORS",
        phase="optional",
        clinical_hint="What makes symptoms better.",
        applies_localised=True,
        applies_non_localised=True,
    ),
    CollectTarget(
        id="social_history",
        category="SOCIAL_HISTORY",
        phase="optional",
        clinical_hint="Smoking/vaping, alcohol, and similar.",
        free_text_policy="optional_other",
        applies_localised=False,
        applies_non_localised=True,
    ),
]

# Always-valid pool for run_devise_and_prioritise(phase="redflag_screening", ...).
# IMMUNISATION_STATUS is banned in optional — deliberately not listed anywhere here.
REDFLAG_SUBCATEGORIES: list[RedFlagSubcategory] = [
    "AIRWAY",
    "BREATHING",
    "CIRCULATION",
    "DISABILITY",
    "TEMPERATURE",
    "OTHER",
]


def _applies_locality(
    target: CollectTarget,
    presentation_category: Optional[str],
) -> bool:
    if presentation_category == "LOCALISED":
        return target.applies_localised
    if presentation_category == "NOT_LOCALISED":
        return target.applies_non_localised
    # Unknown / unset — do not over-filter (same as Pilot appliesLocality fallback).
    return True


def get_eligible_targets(
    phase: CollectPhase,
    patient_sex: Optional[str] = None,
    presentation_category: Optional[str] = None,
) -> list[CollectTarget]:
    """Deterministic filtering — no LLM call.

    Filters by ``requires_patient_sex`` and locality flags. Already-known
    status is conveyed via ``known_collect_values`` on agent context (not
    this function).
    """
    pool = PRIORITY_TARGETS if phase == "priority" else OPTIONAL_TARGETS
    return [
        t
        for t in pool
        if (t.requires_patient_sex is None or t.requires_patient_sex == patient_sex)
        and _applies_locality(t, presentation_category)
    ]


def targets_for_session_phase(
    session_phase: str,
    patient_sex: Optional[str] = None,
    presentation_category: Optional[str] = None,
) -> list[CollectTarget]:
    """Graph/QG phase → filtered collect targets (empty when phase has no pool).

    Used by Devise (candidate_pool) and QG (eligible_targets). Redflag /
    clarify phases are not in ``SESSION_TO_COLLECT_PHASE`` and return ``[]``.
    """
    collect_phase = SESSION_TO_COLLECT_PHASE.get(session_phase)
    if collect_phase is None:
        return []
    return get_eligible_targets(collect_phase, patient_sex, presentation_category)
