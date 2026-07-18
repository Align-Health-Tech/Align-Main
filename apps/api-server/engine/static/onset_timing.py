"""Shared onset/duration timing chips (Shorecare / Pilot canon)."""
from __future__ import annotations

from schemas.question_fields import QuestionOption

ONSET_TIMING_OPTIONS: list[QuestionOption] = [
    QuestionOption(value="LAST_24_HOURS", label="Last 24 hours"),
    QuestionOption(value="WITHIN_48_HOURS", label="Within 48 hours"),
    QuestionOption(value="WITHIN_1_WEEK", label="Within 1 week"),
    QuestionOption(value="MORE_THAN_1_WEEK", label="More than 1 week"),
]


def onset_timing_label(value: str) -> str:
    """Map canon value → English label; fall back to raw string."""
    for opt in ONSET_TIMING_OPTIONS:
        if opt.value == value:
            return opt.label
    return value


def onset_timing_default(stored_text: str | None) -> str | None:
    """Prefill default_value only when stored text matches a timing option."""
    if not stored_text or not stored_text.strip():
        return None
    text = stored_text.strip()
    for opt in ONSET_TIMING_OPTIONS:
        if text == opt.value or text == opt.label:
            return opt.value
    return None
