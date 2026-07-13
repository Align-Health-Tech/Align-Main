"""review — internal-only: write encounter_summary for clinician dashboard, no patient interrupt."""
from __future__ import annotations

from langgraph.types import Command

from engine.completed_phases import with_completed
from schemas.session_states import SessionState

_PHASE = "review"

fake_nurse_call_count = 0


def reset_review_fakes() -> None:
    global fake_nurse_call_count
    fake_nurse_call_count = 0


def _fake_nurse_summary(state: SessionState) -> str:
    global fake_nurse_call_count
    fake_nurse_call_count += 1
    cc = (state.chief_complaint or {}).get("text") or "unspecified complaint"
    cat = state.presentation_category or "UNKNOWN"
    return f"Patient reports {cc} ({cat})."


def review(state: SessionState) -> Command:
    """Silent pass-through — dashboard reads encounter_summary; patient never pauses here."""
    summary = _fake_nurse_summary(state)
    return Command(
        update={
            "encounter_summary": summary,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="complete",
    )
