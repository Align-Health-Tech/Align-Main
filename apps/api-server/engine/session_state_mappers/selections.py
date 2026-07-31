"""Shared answer → Selection parsing for apply mappers."""
from __future__ import annotations

from typing import Any, NamedTuple, Optional

from engine.session_state_mappers.shared import _YES
from engine.session_state_mappers.narrative import narrative_dump_free_text, narrative_dump_option
from schemas.literals import IntakeFactKind
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import IntakeFactState, SessionState


class Selection(NamedTuple):
    """One parsed answer chip.

    ``en_text`` carries the option's ``en_label`` through to
    ``NarrativeField.en_text``. Without it a non-English session stored only the
    localised label, so the clinician dashboard — which must be English — had no
    English for any option pick. Free text has no ``en_label``; it gets
    translated instead (Pattern E).
    """

    text: str
    is_free: bool
    en_text: Optional[str] = None

_EMPTY_SELECTIONS = frozenset(
    {
        "none",
        "none of these",
        "no",
    }
)
_EMPTY_SELECTION_PREFIXES = (
    "none of these",
    "no allergies",
    "no known allergies",
)


def labels_by_folded(question: QuestionField) -> dict[str, tuple[str, Optional[str]]]:
    """value -> (patient-facing label, English label if the session is not English)."""
    return {
        (opt.value or "").strip().casefold(): (opt.label, opt.en_label)
        for opt in (question.options or [])
        if isinstance(opt, QuestionOption)
    }


def parse_chip(
    raw: object,
    labels: dict[str, tuple[str, Optional[str]]],
) -> Selection | None:
    """Parse one answer chip, or None to skip."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    folded = text.casefold()
    if (
        folded in _EMPTY_SELECTIONS
        or folded.startswith(_EMPTY_SELECTION_PREFIXES)
        or folded == "other"
    ):
        return None
    if folded.startswith("other:"):
        detail = text.split(":", 1)[1].strip()
        return Selection(detail, True) if detail else None
    entry = labels.get(folded)
    if entry:
        label, en_label = entry
        return Selection(label, False, en_label)
    # Unknown token — treat as free text so Pattern E translate can run.
    return Selection(text, True)


def selections_for_target(
    questions: list[QuestionField],
    by_id: dict[str, Any],
    target_id: str,
) -> list[Selection] | None:
    """Parse all answered questions for ``target_id``.

    Returns:
      - ``None`` — target not answered (leave prior state)
      - ``[]`` — answered but empty / declined (e.g. None of these, parent No)
      - non-empty list — Selection rows
    """
    qs = [q for q in questions if q.collect_target_id == target_id]
    if not qs or not any(q.id in by_id for q in qs):
        return None

    declined = False
    selected: list[Selection] = []
    saw_content_kind = False
    for question in qs:
        if question.id not in by_id:
            continue
        raw = by_id[question.id]
        if question.kind == "yes_no":
            if raw in _YES:
                continue
            if raw in (False, "no", "false", "No", "False") or (
                isinstance(raw, str) and raw.strip().casefold() == "no"
            ):
                declined = True
            continue

        saw_content_kind = True
        if question.kind == "free_text":
            text = str(raw).strip() if raw is not None else ""
            if text:
                selected.append(Selection(text, True))
            continue

        if question.kind not in ("multi_choice", "single_choice"):
            continue
        labels = labels_by_folded(question)
        values = raw if isinstance(raw, list) else [raw]
        for item in values:
            parsed = parse_chip(item, labels)
            if parsed is not None:
                selected.append(parsed)

    if declined and not selected:
        return []
    if not saw_content_kind and not declined:
        # Only a yes_no gate was answered (e.g. parent Yes with no follow-up).
        return None
    return selected


def narrative_dumps(
    state: SessionState,
    selections: list[Selection],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for selection in selections:
        key = selection.text.casefold()
        if not selection.text or key in seen:
            continue
        seen.add(key)
        if selection.is_free:
            out.append(
                narrative_dump_free_text(
                    selection.text, session_language=state.session_language
                )
            )
        else:
            out.append(
                narrative_dump_option(selection.text, en_label=selection.en_text)
            )
    return out


def join_narrative(
    state: SessionState,
    selections: list[Selection],
) -> dict[str, Any] | None:
    """Collapse multi-select into one NarrativeField (e.g. self_management)."""
    dumps = narrative_dumps(state, selections)
    if not dumps:
        return None
    if len(dumps) == 1:
        return dumps[0]
    # Prefer free_text source if any part was free text.
    texts = [str(d.get("text", "")) for d in dumps if d.get("text")]
    joined = "; ".join(texts)
    if any(d.get("source") == "free_text" for d in dumps):
        return narrative_dump_free_text(
            joined, session_language=state.session_language
        )
    # All-or-nothing on the English side: a partly-English join would read as a
    # complete translation to a clinician.
    en_parts = [d.get("en_text") for d in dumps]
    joined_en = (
        "; ".join(str(part) for part in en_parts)
        if all(part for part in en_parts)
        else None
    )
    return narrative_dump_option(joined, en_label=joined_en)


def intake_fact_additions(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
    targets: dict[str, IntakeFactKind],
) -> list[dict[str, Any]]:
    """Build new intake_fact rows for each answered target in ``targets``."""
    additions: list[dict[str, Any]] = []
    for target_id, kind in targets.items():
        sels = selections_for_target(questions, by_id, target_id)
        if not sels:
            continue
        for dump in narrative_dumps(state, sels):
            additions.append(
                IntakeFactState(
                    kind=kind,
                    source="PATIENT_INTAKE",
                    display=dump,
                ).model_dump()
            )
    return additions


def merge_intake_facts(
    state: SessionState,
    additions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Append ``additions`` to existing facts, deduping by (kind, display text)."""
    facts = list(state.intake_facts)
    seen = {_fact_key(fact) for fact in facts}
    for fact in additions:
        key = _fact_key(fact)
        if key in seen:
            continue
        seen.add(key)
        facts.append(fact)
    return facts


def _fact_key(fact: dict[str, Any]) -> tuple[str, str]:
    display = fact.get("display")
    text = display.get("text", "") if isinstance(display, dict) else ""
    return str(fact.get("kind", "")).casefold(), str(text).strip().casefold()
