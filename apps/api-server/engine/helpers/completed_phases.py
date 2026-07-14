"""Append phase names to SessionState.completed_phases without duplicates."""
from __future__ import annotations

from schemas.session_states import SessionState


def with_completed(state: SessionState, phase: str) -> list[str]:
    completed = list(state.completed_phases)
    if phase not in completed:
        completed.append(phase)
    return completed
