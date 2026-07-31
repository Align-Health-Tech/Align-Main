"""priority_questions answers → SessionState / intake_facts."""
from __future__ import annotations

from typing import Any

from engine.session_state_mappers.selections import (
    Selection,
    intake_fact_additions,
    merge_intake_facts,
    narrative_dumps,
    selections_for_target,
)
from engine.session_state_mappers.shared import _YES
from engine.session_state_mappers.narrative import narrative_dump_free_text, narrative_dump_option
from schemas.literals import IntakeFactKind
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState

# collect_target_id → intake_fact kind
_INTAKE_FACT_TARGETS: dict[str, IntakeFactKind] = {
    "allergy": "ALLERGY",
}


def map_priority_questions(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    """Map priority collect targets onto SessionState."""
    updates: dict[str, Any] = {}

    med = _apply_encounter_medication(state, questions, by_id)
    if med is not None:
        updates["encounter_medication"] = med

    preg = _apply_pregnancy_possible(questions, by_id)
    if preg is not None:
        updates["pregnancy_possible"] = preg

    character = selections_for_target(questions, by_id, "character")
    if character is not None:
        updates["character"] = narrative_dumps(state, character)

    onset = selections_for_target(questions, by_id, "onset_circumstance")
    if onset:
        updates["onset_circumstance"] = _onset_narrative(state, onset)

    comorbidities = selections_for_target(questions, by_id, "comorbidities")
    if comorbidities is not None:
        updates["comorbidities"] = narrative_dumps(state, comorbidities)

    fact_additions = intake_fact_additions(
        state, questions, by_id, _INTAKE_FACT_TARGETS
    )
    if fact_additions:
        updates["intake_facts"] = merge_intake_facts(state, fact_additions)

    return updates


def _onset_narrative(
    state: SessionState,
    selections: list[Selection],
) -> dict[str, Any]:
    """Singular onset field — option chips or free text."""
    selection = selections[0]
    if not selection.is_free:
        return narrative_dump_option(selection.text, en_label=selection.en_text)
    return narrative_dump_free_text(
        selection.text, session_language=state.session_language
    )


def _apply_encounter_medication(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> list[dict[str, Any]] | None:
    sels = selections_for_target(questions, by_id, "medication")
    if sels is None:
        return None
    return narrative_dumps(state, sels)


def _apply_pregnancy_possible(
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> bool | None:
    for q in questions:
        if q.collect_target_id != "pregnancy":
            continue
        if q.id not in by_id:
            continue
        val = by_id[q.id]
        if val in _YES or val in ("Yes",):
            return True
        if val in (False, "no", "false", "No", "False"):
            return False
        if isinstance(val, str) and val.strip().casefold() in ("yes", "no"):
            return val.strip().casefold() == "yes"
    return None
