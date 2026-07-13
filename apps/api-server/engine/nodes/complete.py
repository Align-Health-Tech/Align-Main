"""Terminal node — marks session complete."""
from __future__ import annotations

from schemas.session_states import SessionState


def complete(state: SessionState) -> dict:
    return {"is_session_complete": True, "awaiting_phase": None, "pending_questions": []}
