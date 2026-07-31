"""Pattern E — free-text → NarrativeField; translate when session_language != en.

Mappers reach AI only via ``engine.agent_bridge.translate_to_english``.
"""
from __future__ import annotations

from engine import agent_bridge
from schemas.jsonb_fields import NarrativeField


def narrative_dump_free_text(
    text: str,
    *,
    session_language: str,
) -> dict:
    return _narrative_from_free_text(
        text, session_language=session_language
    ).model_dump()


def narrative_dump_option(label: str, *, en_label: str | None = None) -> dict:
    return _narrative_from_option(label, en_label=en_label).model_dump()


# ---------------------------------------------------------------------------
# Internal helpers (private — not part of the public surface)
# ---------------------------------------------------------------------------


def _narrative_from_free_text(
    text: str,
    *,
    session_language: str,
) -> NarrativeField:
    """Patient free text. Translate when not English."""
    if session_language == "en":
        return NarrativeField(text=text, source="free_text")
    # Module attribute lookup so CI patches on engine.agent_bridge apply.
    translated = agent_bridge.translate_to_english(text, session_language)
    return NarrativeField(
        text=text,
        en_text=translated.en_text,
        source="free_text",
    )


def _narrative_from_option(
    label: str, *, en_label: str | None = None
) -> NarrativeField:
    """Option pick — no translation call; QG already supplied the English.

    ``en_label`` is None for English sessions (``label`` is already English) and
    also when QG failed to emit one — the clinician dashboard shows the gap
    rather than passing a localised label off as English.
    """
    return NarrativeField(text=label, en_text=en_label, source="option")
