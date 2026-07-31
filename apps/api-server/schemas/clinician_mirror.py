"""Clinician read model — what the patient said, in their words and in English.

``NextStep`` only carries questions out to the patient; it never carries answers
back. So the demo frontend rebuilt the clinician pane from whatever it had just
submitted, which meant free text stayed in the patient's language. Translation
already happens server-side (``narrative.py`` calls
``agent_bridge.translate_to_english`` and stores ``NarrativeField.en_text``) —
this is the projection that exposes it.

Derived from SessionState only: no writes, no LLM calls.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from schemas.session_states import SessionState

# SessionState attr -> collect_target_id, single-valued narrative columns,
# in the order a clinician reads them.
_SCALAR_NARRATIVES: tuple[str, ...] = (
    "chief_complaint",
    "duration",
    "persistence",
    "progression",
    "onset_circumstance",
    "self_management",
    "ice_idea",
    "ice_concern",
    "ice_expectation",
)

# Same, list-valued.
_LIST_NARRATIVES: tuple[str, ...] = (
    "character",
    "mitigating_factors",
    "exacerbating_factors",
    "comorbidities",
    "encounter_medication",
)


class MirrorField(BaseModel):
    collect_target_id: str
    #: Patient's own wording.
    text: str
    #: English. None when the session is already English — then ``text`` is the
    #: English and there is no translation to show.
    en_text: Optional[str] = None
    #: option | free_text | ai_summary
    source: Optional[str] = None


class ClinicianMirror(BaseModel):
    session_language: str = "en"
    #: One-line English synthesis from the nurse-review agent. Written in
    #: English directly, so it has no native counterpart.
    encounter_summary: Optional[str] = None
    fields: list[MirrorField] = []


def _field(dump: Any, collect_target_id: str) -> Optional[MirrorField]:
    """NarrativeField dump -> MirrorField; skips anything with no text."""
    if not isinstance(dump, dict):
        return None
    text = dump.get("text")
    if not isinstance(text, str) or not text:
        return None
    return MirrorField(
        collect_target_id=collect_target_id,
        text=text,
        en_text=dump.get("en_text"),
        source=dump.get("source"),
    )


def build_clinician_mirror(state: Optional[SessionState]) -> ClinicianMirror:
    """Project a checkpointed SessionState. None (pre-graph) -> empty mirror."""
    if state is None:
        return ClinicianMirror()

    fields: list[MirrorField] = []

    for attr in _SCALAR_NARRATIVES:
        found = _field(getattr(state, attr, None), attr)
        if found is not None:
            fields.append(found)

    for attr in _LIST_NARRATIVES:
        for dump in getattr(state, attr, None) or []:
            found = _field(dump, attr)
            if found is not None:
                fields.append(found)

    # intake_facts nest their narrative under `display`, and what matters
    # clinically is the fact kind (ALLERGY / MEDICATION / ...), not the column.
    for fact in state.intake_facts or []:
        if not isinstance(fact, dict):
            continue
        kind = str(fact.get("kind") or "unknown").lower()
        found = _field(fact.get("display"), f"intake_fact.{kind}")
        if found is not None:
            fields.append(found)

    return ClinicianMirror(
        session_language=state.session_language,
        encounter_summary=state.encounter_summary,
        fields=fields,
    )
