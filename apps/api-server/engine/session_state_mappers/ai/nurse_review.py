"""nurse review agent → encounter_summary."""
from __future__ import annotations

from typing import Any

from schemas.clinical_ai_io import ReviewSummaryResult
from schemas.session_states import SessionState


def map_nurse_review(
    _state: SessionState,
    result: ReviewSummaryResult,
) -> dict[str, Any]:
    """Map ``ReviewSummaryResult`` onto SessionState update fields."""
    return {"encounter_summary": result.summary}
