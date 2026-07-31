"""Per-phase QuestionField constraints after QG (fail loudly on LLM drift). """
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from schemas.question_fields import QuestionField

QuestionValidator = Callable[[str, QuestionField], None]
BatchValidator = Callable[[str, list[QuestionField]], None]

_NL_CLARIFY_VALUES_IN_ORDER = (
    "Yes",
    "No",
    "I don't know",
)
_ICE_TARGETS_IN_ORDER = (
    "ice_idea",
    "ice_concern",
    "ice_expectation",
)
_ALLOWED_OPTIONAL_TARGETS = frozenset(
    {
        "past_history",
        "family_history",
        "self_management",
        "weight_change",
        "exacerbating_factors",
        "mitigating_factors",
        "social_history",
    }
)


@dataclass(frozen=True)
class PhaseValidationPolicy:
    """Validation rules applied to one question-generation phase."""

    allow_empty: bool = False
    max_questions: int | None = None
    question_validator: QuestionValidator | None = None
    batch_validator: BatchValidator | None = None


def phase_max_questions(phase: str) -> int | None:
    """Return the phase policy's ``max_questions`` (if any)."""
    try:
        return _PHASE_POLICIES[phase].max_questions
    except KeyError as exc:
        raise ValueError(f"Unknown QG phase {phase!r}") from exc


def validate_qg_questions(
    phase: str,
    questions: list[QuestionField],
) -> None:
    """Validate generated questions against the policy for ``phase``. 
    
    If this function raises an error, then the QG process should be restarted and this prevents 
    wrong format of questions being sent to the User. 
    """
    try:
        policy = _PHASE_POLICIES[phase]
    except KeyError as exc:
        raise ValueError(f"Unknown QG phase {phase!r}") from exc

    if not questions:
        if policy.allow_empty:
            return
        raise ValueError(
            f"QG phase {phase!r}: expected at least one question, got none"
        )

    if (
        policy.max_questions is not None
        and len(questions) > policy.max_questions
    ):
        raise ValueError(
            f"QG phase {phase!r}: expected at most "
            f"{policy.max_questions} questions, got {len(questions)}"
        )

    if policy.batch_validator is not None:
        policy.batch_validator(phase, questions)

    if policy.question_validator is not None:
        for question in questions:
            policy.question_validator(phase, question)


def _validate_presenting_complaint_question(
    phase: str,
    question: QuestionField,
) -> None:
    if question.kind != "single_choice":
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"kind must be 'single_choice', got {question.kind!r}"
        )
    options = question.options or []
    if not 2 <= len(options) <= 5:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"expected 2–5 options, got {len(options)}"
        )
    values = [option.value for option in options]
    labels = [option.label for option in options]
    if "Other" not in values and "Other" not in labels:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"options must include 'Other'; got values={values!r}"
        )


def _validate_non_localised_question(
    phase: str,
    question: QuestionField,
) -> None:
    if question.kind != "single_choice":
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"kind must be 'single_choice', got {question.kind!r}"
        )
    values = tuple(option.value for option in (question.options or []))
    if values != _NL_CLARIFY_VALUES_IN_ORDER:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"option values must be exactly "
            f"{_NL_CLARIFY_VALUES_IN_ORDER!r}, got {values!r}"
        )


def _validate_priority_question(
    phase: str,
    question: QuestionField,
) -> None:
    """Comorbidities must be multi-choice with a none option and no Other."""
    target_id = (question.collect_target_id or question.id or "").casefold()
    if target_id != "comorbidities" and "comorbid" not in target_id:
        return
    if question.kind != "multi_choice":
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"comorbidities kind must be 'multi_choice', got {question.kind!r}"
        )
    values = [option.value for option in (question.options or [])]
    if "Other" in values:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"comorbidities must not use 'Other'; got values={values!r}"
        )
    if "None of these" not in values:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            "comorbidities must include 'None of these'; "
            f"got values={values!r}"
        )


def _validate_redflag_question(
    phase: str,
    question: QuestionField,
) -> None:
    if question.kind != "yes_no":
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"kind must be 'yes_no', got {question.kind!r}"
        )


def _validate_optional_question(
    phase: str,
    question: QuestionField,
) -> None:
    if question.required:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            "required must be false"
        )
    if question.collect_target_id not in _ALLOWED_OPTIONAL_TARGETS:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            "collect_target_id must be one of "
            f"{sorted(_ALLOWED_OPTIONAL_TARGETS)!r}, "
            f"got {question.collect_target_id!r}"
        )
    if question.kind == "multi_choice":
        values = [option.value for option in (question.options or [])]
        value_set = set(values)
        if "Other" not in value_set and "other" not in value_set:
            raise ValueError(
                f"QG phase {phase!r} question {question.id!r}: "
                "multi_choice options must include 'Other' or 'other'; "
                f"got values={values!r}"
            )


def _validate_ice_batch(
    phase: str,
    questions: list[QuestionField],
) -> None:
    ids = tuple(question.id for question in questions)
    targets = tuple(question.collect_target_id for question in questions)
    if ids != _ICE_TARGETS_IN_ORDER or targets != _ICE_TARGETS_IN_ORDER:
        raise ValueError(
            f"QG phase {phase!r}: expected exactly "
            f"{_ICE_TARGETS_IN_ORDER!r} in order; "
            f"got ids={ids!r}, collect_target_ids={targets!r}"
        )


def _validate_ice_question(
    phase: str,
    question: QuestionField,
) -> None:
    if question.kind != "multi_choice":
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"kind must be 'multi_choice', got {question.kind!r}"
        )
    options = question.options or []
    if not 3 <= len(options) <= 5:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"expected 3–6 options (chips + Other), got {len(options)}"
        )
        
    value_labels = {option.value: option.label for option in options}
    # Checks `value`, never `label`: value is the machine key and stays English,
    # while label is patient-facing and must be in the session language ("기타",
    # "其他", …). Requiring label == "Other" made a localised session unroutable.
    if "Other" not in value_labels:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"options must include an 'Other' value; got value_labels={value_labels!r}"
        )



def _validate_duration_batch(
    phase: str,
    questions: list[QuestionField],
) -> None:
    if len(questions) != 1:
        raise ValueError(
            f"QG phase {phase!r}: expected exactly 1 question, "
            f"got {len(questions)}"
        )


def _validate_duration_question(
    phase: str,
    question: QuestionField,
) -> None:
    if question.collect_target_id != "duration":
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"collect_target_id must be 'duration', "
            f"got {question.collect_target_id!r}"
        )
    if question.kind != "single_choice":
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"kind must be 'single_choice', got {question.kind!r}"
        )
    options = question.options or []
    if not 3 <= len(options) <= 6:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"expected 3–6 options (chips + Other), got {len(options)}"
        )
    value_labels = {option.value: option.label for option in options}
    # Checks `value`, never `label`: value is the machine key and stays English,
    # while label is patient-facing and must be in the session language ("기타",
    # "其他", …). Requiring label == "Other" made a localised session unroutable.
    if "Other" not in value_labels:
        raise ValueError(
            f"QG phase {phase!r} question {question.id!r}: "
            f"options must include an 'Other' value; got value_labels={value_labels!r}"
        )


_PHASE_POLICIES: dict[str, PhaseValidationPolicy] = {
    "presenting_complaint_clarify": PhaseValidationPolicy(
        question_validator=_validate_presenting_complaint_question,
    ),
    "non_localised_clarify": PhaseValidationPolicy(
        question_validator=_validate_non_localised_question,
    ),
    "priority_questions": PhaseValidationPolicy(
        question_validator=_validate_priority_question,
    ),
    "redflag_screening": PhaseValidationPolicy(
        allow_empty=True,
        # Devise ≤3 topics × ≤3 findings/topic → hard cap 9.
        max_questions=9,
        question_validator=_validate_redflag_question,
    ),
    "optional_questions": PhaseValidationPolicy(
        allow_empty=True,
        max_questions=4,
        question_validator=_validate_optional_question,
    ),
    "ice": PhaseValidationPolicy(
        batch_validator=_validate_ice_batch,
        question_validator=_validate_ice_question,
    ),
    "duration": PhaseValidationPolicy(
        max_questions=1,
        batch_validator=_validate_duration_batch,
        question_validator=_validate_duration_question,
    ),
}
