"""Priority/optional/redflag candidate pools + get_eligible_targets() filter."""
from typing import Optional

from schemas.collect_targets import CollectPhase, CollectTarget, RedFlagSubcategory

Phase = CollectPhase


PRIORITY_TARGETS: list[CollectTarget] = [
    CollectTarget(
        id="medication",
        category="MEDICATION_MANAGEMENT",
        phase="priority",
        clinical_hint="Usual meds, meds for this symptom, OTC vs prescribed, efficacy, side effects.",
        example_prompt="Are you taking any medicines for your current symptoms?",
        suggested_options=["Panadol", "Ibuprofen", "Voltaren", "Other"],
        free_text_policy="optional_other",
    ),
    CollectTarget(
        id="symptom_characteristics",
        category="SYMPTOM_CHARACTERISTIC",
        phase="priority",
        clinical_hint="Frequency, persistence, pain quality, tenderness.",
        example_prompt="How does the pain feel?",
        suggested_options=["Sharp", "Dull or aching", "Burning", "Throbbing", "Other"],
        free_text_policy="optional_other",
    ),
    CollectTarget(
        id="onset_circumstance",
        category="ONSET_CIRCUMSTANCE",
        phase="priority",
        clinical_hint="Mainly localised; non-localised presentations often skip this target.",
        example_prompt="How did this happen?",
        suggested_options=[
            "I fell down",
            "I twisted it",
            "I bumped it",
            "It came on by itself",
            "Other",
        ],
        free_text_policy="optional_other",
    ),
    CollectTarget(
        id="allergy",
        category="ALLERGY",
        phase="priority",
        example_prompt="Do you have any allergies?",
        suggested_options=["Medicines", "Food", "Insects or stings", "Latex", "Other"],
        free_text_policy="optional_other",
    ),
    CollectTarget(
        id="comorbidities",
        category="COMORBIDITIES",
        phase="priority",
        example_prompt="Are you currently being treated for any long-term conditions?",
        suggested_options=[
            "Diabetes",
            "High blood pressure",
            "Asthma",
            "Heart conditions",
            "None of these",
        ],
        free_text_policy="avoid",
    ),
    CollectTarget(
        id="pregnancy",
        category="PREGNANCY",
        phase="priority",
        example_prompt="Is there any chance you could be pregnant?",
        suggested_options=["No", "Yes"],
        requires_patient_sex="female",
    ),
]

OPTIONAL_TARGETS: list[CollectTarget] = [
    CollectTarget(
        id="past_history",
        category="PAST_HISTORY",
        phase="optional",
        example_prompt=(
            "Have you had any major surgeries or been in hospital for a serious condition before?"
        ),
        suggested_options=[
            "Major surgery",
            "Hospital stay for serious illness",
            "Cancer treatment in the past",
            "Other",
        ],
        free_text_policy="optional_other",
    ),
    CollectTarget(
        id="family_history",
        category="FAMILY_HISTORY",
        phase="optional",
        example_prompt=(
            "Does anyone in your immediate family have any major ongoing health conditions?"
        ),
        suggested_options=["Heart disease", "Diabetes", "Cancer", "Stroke", "Other"],
        free_text_policy="optional_other",
    ),
    CollectTarget(
        id="self_management",
        category="SELF_MANAGEMENT",
        phase="optional",
        example_prompt=(
            "Have you tried anything yourself to manage this before coming in today?"
        ),
        suggested_options=[
            "Took painkillers from the pharmacy",
            "Used heat or ice",
            "Rested it",
            "Used a bandage or support",
            "Other",
        ],
        free_text_policy="optional_other",
    ),
    CollectTarget(id="weight_change", category="WEIGHT_CHANGE", phase="optional"),
    CollectTarget(
        id="exacerbating_factors", category="EXACERBATING_FACTORS", phase="optional"
    ),
    CollectTarget(
        id="mitigating_factors", category="MITIGATING_FACTORS", phase="optional"
    ),
    CollectTarget(
        id="social_history",
        category="SOCIAL_HISTORY",
        phase="optional",
        example_prompt="Which of the following currently apply to you?",
        suggested_options=[
            "I smoke or vape",
            "I drink alcohol regularly",
            "None of these",
            "Other",
        ],
        free_text_policy="optional_other",
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


def get_eligible_targets(
    phase: Phase,
    already_known_ids: set[str],
    patient_sex: Optional[str] = None,
) -> list[CollectTarget]:
    """Deterministic filtering — no LLM call."""
    pool = PRIORITY_TARGETS if phase == "priority" else OPTIONAL_TARGETS
    return [
        t
        for t in pool
        if t.id not in already_known_ids
        and (t.requires_patient_sex is None or t.requires_patient_sex == patient_sex)
    ]
