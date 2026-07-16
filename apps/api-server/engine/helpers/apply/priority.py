"""priority_questions answers → encounter_medication / pregnancy_possible.

Other priority collect targets (character, onset, allergy, comorbidities) are
asked for prefill-and-confirm but persistence for those paths is not wired
here yet — only medication + pregnancy write through today.
"""
from __future__ import annotations

from typing import Any

from engine.helpers.apply.shared import _YES
from engine.helpers.translate import narrative_dump_free_text, narrative_dump_option
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


def apply_priority_questions(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    """Map priority collect targets onto SessionState."""
    updates: dict[str, Any] = {}
    med_update = _apply_encounter_medication(state, questions, by_id)
    if med_update is not None:
        updates["encounter_medication"] = med_update
    preg = _apply_pregnancy_possible(questions, by_id)
    if preg is not None:
        updates["pregnancy_possible"] = preg
    return updates


def _apply_encounter_medication(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> list[dict[str, Any]] | None:
    """Build encounter_medication from medication-target answers.

    Supports flat multi_choice and/or yes_no (+ separate multi_choice) questions
    that share ``collect_target_id=\"medication\"``. Returns ``None`` when no
    medication question was answered (leave prior state untouched).
    """
    med_qs = [q for q in questions if q.collect_target_id == "medication"]
    if not med_qs:
        return None
    if not any(q.id in by_id for q in med_qs):
        return None

    declined = False
    selected: list[str] = []
    option_labels: set[str] = set()
    for q in med_qs:
        for opt in q.options or []:
            option_labels.add(opt.value)
            option_labels.add(opt.label)
        val = by_id.get(q.id)
        if val is None or val == "":
            continue
        if q.kind == "yes_no":
            if val not in _YES and val not in (False, "no", "false", "No", "False"):
                continue
            if val not in _YES:
                declined = True
            continue
        if isinstance(val, list):
            selected.extend(str(v) for v in val if v is not None and v != "")
        else:
            selected.append(str(val))

    if declined and not selected:
        return []

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in selected:
        text, is_free = _medication_answer_text(raw, option_labels)
        if not text or text.casefold() in seen:
            continue
        seen.add(text.casefold())
        if is_free:
            entries.append(
                narrative_dump_free_text(
                    text, session_language=state.session_language
                )
            )
        else:
            entries.append(narrative_dump_option(text))
    return entries


def _medication_answer_text(
    raw: str,
    option_labels: set[str],
) -> tuple[str, bool]:
    """Return (display text, is_free_text).

    Recognises ``Other: fish oil`` / bare free-text that is not a listed option.
    Skips a lone ``Other`` with no detail.
    """
    stripped = raw.strip()
    if not stripped:
        return "", False
    lower = stripped.casefold()
    if lower == "other":
        return "", False
    if lower.startswith("other:"):
        detail = stripped.split(":", 1)[1].strip()
        return (detail, True) if detail else ("", False)
    if stripped in option_labels:
        return stripped, False
    return stripped, True


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
