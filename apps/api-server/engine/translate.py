"""Pattern E — free-text → NarrativeField; fake translate when session_language != en."""
from __future__ import annotations

from schemas.jsonb_fields import NarrativeField

fake_translate_call_count = 0


def reset_translate_fakes() -> None:
    global fake_translate_call_count
    fake_translate_call_count = 0


def narrative_from_free_text(
    text: str,
    *,
    session_language: str,
) -> NarrativeField:
    """Patient free text. Translate when not English (fake until M5)."""
    global fake_translate_call_count
    if session_language == "en":
        return NarrativeField(text=text, source="free_text")
    fake_translate_call_count += 1
    return NarrativeField(
        text=text,
        en_text=f"[en] {text}",
        source="free_text",
    )


def narrative_from_option(label: str) -> NarrativeField:
    """Option pick — no translation call."""
    return NarrativeField(text=label, source="option")


def narrative_dump_free_text(
    text: str,
    *,
    session_language: str,
) -> dict:
    return narrative_from_free_text(text, session_language=session_language).model_dump()


def narrative_dump_option(label: str) -> dict:
    return narrative_from_option(label).model_dump()
