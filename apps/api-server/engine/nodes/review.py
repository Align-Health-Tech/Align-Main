"""review — internal-only: write encounter_summary for clinician dashboard, no patient interrupt."""
from __future__ import annotations

from langgraph.types import Command

from engine import agent_bridge
from engine.session_state_mappers import map_ai_result
from engine.helpers.completed_phases import with_completed
from schemas.session_states import SessionState

_PHASE = "review"


def review(state: SessionState) -> Command:
    """Silent pass-through — dashboard reads encounter_summary; patient never pauses here."""
    result = agent_bridge.run_nurse_review_summary_agent(
        agent_bridge.build_agent_context(state)
    )
    return Command(
        update={
            **map_ai_result(state, result),
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="complete",
    )
