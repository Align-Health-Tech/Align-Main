"""Per-phase QuestionField constraints after QG (fail loudly on LLM drift).

Registered phases always run (including placeholders that currently no-op).
"""
from __future__ import annotations

from schemas.question_fields import QuestionField

_NL_CLARIFY_VALUES = ("Yes", "No", "I don't know")


def validate_qg_questions(phase: str, questions: list[QuestionField]) -> None:
    """Raise ValueError if ``questions`` violate known constraints for ``phase``."""
    validator = _VALIDATORS.get(phase)
    if validator is None:
        return
    if not questions:
        raise ValueError(
            f"QG phase {phase!r}: expected at least one question, got none"
        )
    for q in questions:
        validator(phase, q)


def _validate_presenting_complaint_clarify(phase: str, q: QuestionField) -> None:
    if q.kind != "single_choice":
        raise ValueError(
            f"QG phase {phase!r} question {q.id!r}: "
            f"kind must be 'single_choice', got {q.kind!r}"
        )
    opts = q.options or []
    n = len(opts)
    if n < 2 or n > 5:
        raise ValueError(
            f"QG phase {phase!r} question {q.id!r}: "
            f"expected 2–5 options, got {n}"
        )
    values = [o.value for o in opts]
    labels = [o.label for o in opts]
    if "Other" not in values and "Other" not in labels:
        raise ValueError(
            f"QG phase {phase!r} question {q.id!r}: "
            f"options must include 'Other' (value or label); got values={values!r}"
        )


def _validate_non_localised_clarify(phase: str, q: QuestionField) -> None:
    if q.kind != "single_choice":
        raise ValueError(
            f"QG phase {phase!r} question {q.id!r}: "
            f"kind must be 'single_choice', got {q.kind!r}"
        )
    opts = q.options or []
    values = tuple(o.value for o in opts)
    if values != _NL_CLARIFY_VALUES:
        raise ValueError(
            f"QG phase {phase!r} question {q.id!r}: "
            f"options values must be exactly {_NL_CLARIFY_VALUES!r}, got {values!r}"
        )


def _validate_priority_questions(phase: str, q: QuestionField) -> None:
    """Comorbidities multi_choice: require 'None of these', ban 'Other'."""
    tid = (q.collect_target_id or q.id or "").casefold()
    if tid != "comorbidities" and "comorbid" not in tid:
        return
    if q.kind != "multi_choice":
        return
    values = [o.value for o in (q.options or [])]
    if "Other" in values:
        raise ValueError(
            f"QG phase {phase!r} question {q.id!r}: "
            f"comorbidities must not use 'Other'; got values={values!r}"
        )
    if "None of these" not in values:
        raise ValueError(
            f"QG phase {phase!r} question {q.id!r}: "
            f"comorbidities must include 'None of these'; got values={values!r}"
        )


def _validate_placeholder(_phase: str, _q: QuestionField) -> None:
    """No-op until this phase's prompt contract is ported."""


_VALIDATORS = {
    "presenting_complaint_clarify": _validate_presenting_complaint_clarify,
    "non_localised_clarify": _validate_non_localised_clarify,
    "priority_questions": _validate_priority_questions,
    # Placeholders — tighten when Devise/QG prompts for these phases ship.
    "redflag_screening": _validate_placeholder,
    "optional_questions": _validate_placeholder,
    "ice": _validate_placeholder,
}
