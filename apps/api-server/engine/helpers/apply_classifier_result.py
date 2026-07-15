"""Apply ClassifierResult fields onto SessionState (hint + intake supplement)."""
from __future__ import annotations

from typing import Any

from engine.helpers.translate import narrative_dump_free_text
from schemas.clinical_ai_io import ClassifierResult, EncounterIntakeSupplement
from schemas.session_states import SessionState

# SessionState narrative list fields filled from supplement string lists.
_NARRATIVE_LIST_FIELDS = (
    "character",
    "mitigating_factors",
    "exacerbating_factors",
    "comorbidities",
)

# SessionState single NarrativeField columns.
_NARRATIVE_SCALAR_FIELDS = (
    "onset_circumstance",
    "duration",
    "persistence",
    "progression",
    "self_management",
)


def apply_classifier_result(
    state: SessionState,
    result: ClassifierResult,
) -> dict[str, Any]:
    """Map a ready classifier result into SessionState update fields.

    Sets ``presentation_category``, overwrites ``chief_complaint`` from
    ``chief_complaint_summary`` when present, stores anatomy sites on
    ``presenting_complaint_hint``, and backfills encounter fields from
    ``encounter_intake_supplement`` (only keys the model actually set).
    """
    category = result.category or "LOCALISED"
    updates: dict[str, Any] = {
        "presentation_category": category,
    }

    if result.chief_complaint_summary:
        updates["chief_complaint"] = _chief_complaint_from_ai_summary(
            result.chief_complaint_summary,
            session_language=state.session_language,
        )

    if result.localised_anatomy_sites:
        updates["presenting_complaint_hint"] = {
            "localisedAnatomySites": [
                site.model_dump(mode="json", by_alias=True)
                for site in result.localised_anatomy_sites
            ]
        }
    else:
        updates["presenting_complaint_hint"] = {}

    if result.encounter_intake_supplement is not None:
        updates.update(
            _supplement_to_state_updates(
                result.encounter_intake_supplement,
                session_language=state.session_language,
            )
        )
    return updates


def _chief_complaint_from_ai_summary(
    summary: str,
    *,
    session_language: str,
) -> dict[str, Any]:
    """LLM English synthesis — not patient free text; no translation call.

    ``en_text``: omitted when session is already English (same pattern as
    ``narrative_dump_free_text``). When session_language != \"en\", set
    ``en_text`` equal to ``text`` so clinician-facing code that expects an
    English companion field still finds one — the summary is already English.
    """
    field: dict[str, Any] = {
        "text": summary,
        "source": "ai_summary",
    }
    if session_language != "en":
        field["en_text"] = summary
    return field


def _supplement_to_state_updates(
    supplement: EncounterIntakeSupplement,
    *,
    session_language: str,
) -> dict[str, Any]:
    """Only include keys the model set (not None)."""
    updates: dict[str, Any] = {}
    data = supplement.model_dump(exclude_none=True)

    for key in _NARRATIVE_SCALAR_FIELDS:
        if key not in data:
            continue
        updates[key] = narrative_dump_free_text(
            str(data[key]), session_language=session_language
        )

    for key in _NARRATIVE_LIST_FIELDS:
        if key not in data:
            continue
        raw_list = data[key]
        if not isinstance(raw_list, list):
            continue
        updates[key] = [
            narrative_dump_free_text(str(item), session_language=session_language)
            for item in raw_list
        ]

    if "weight_change" in data:
        updates["weight_change"] = str(data["weight_change"])
    if "acc_claim_suspected" in data:
        updates["acc_claim_suspected"] = bool(data["acc_claim_suspected"])
    if "acc_can_work" in data:
        updates["acc_can_work"] = bool(data["acc_can_work"])

    return updates
