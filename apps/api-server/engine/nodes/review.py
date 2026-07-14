"""review — internal-only: write encounter_summary for clinician dashboard, no patient interrupt."""
from __future__ import annotations

from langgraph.types import Command

from engine.helpers import agent_bridge
from engine.helpers.completed_phases import with_completed
from schemas.session_states import SessionState

_PHASE = "review"


def review(state: SessionState) -> Command:
    """Silent pass-through — dashboard reads encounter_summary; patient never pauses here."""
    summary = agent_bridge.run_nurse_review_summary_agent(
        agent_bridge.build_agent_context(state)
    ).summary
    return Command(
        update={
            "encounter_summary": summary,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="complete",
    )
