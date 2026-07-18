"""Body-diagram resume → body_structures."""
from __future__ import annotations

from typing import Any

from engine.static.body_diagram_catalogue import laterality_for_region_id, resolve_coding
from schemas.session_states import SessionState


def map_body_diagram(state: SessionState, answer: Any) -> dict[str, Any]:
    """Handle body_diagram resume: ``{"region_id": "Select_RightAnkle"}``."""
    payload = answer if isinstance(answer, dict) else {}
    region_id = payload.get("region_id")
    if not isinstance(region_id, str) or not region_id.strip():
        raise ValueError(f"body_diagram answer missing region_id: {answer!r}")

    coding = resolve_coding(region_id)
    if coding is None:
        raise ValueError(f"Unrecognised region_id from client: {region_id!r}")

    return {
        "turn_number": state.turn_number + 1,
        "body_structures": [
            {
                "region_detail": coding.model_dump(),
                "laterality": laterality_for_region_id(region_id),
                "severity_score": None,
                "sub_region_detail": None,
                "radiation_status": None,
                "character": [],
                "radiation_sites": [],
            }
        ],
    }
