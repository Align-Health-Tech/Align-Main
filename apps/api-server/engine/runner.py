"""Start / resume helpers mapping interrupts to NextStep."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from langgraph.types import Command

from engine.graph import build_graph
from engine.next_step import next_step_from_state
from schemas.question_fields import NextStep
from schemas.session_states import SessionState

__all__ = ["SessionRunner", "NextStep"]


class SessionRunner:
    def __init__(self) -> None:
        self._graph = build_graph()

    def start(
        self,
        *,
        session_id: str | None = None,
        patient_id: str | None = None,
        organization_id: str | None = None,
        session_language: str = "en",
    ) -> tuple[str, NextStep]:
        sid = session_id or str(uuid4())
        initial = SessionState(
            session_id=sid,
            patient_id=patient_id or str(uuid4()),
            organization_id=organization_id or str(uuid4()),
            session_language=session_language,
        )
        config = {"configurable": {"thread_id": sid}}
        result = self._graph.invoke(initial, config)
        return sid, self._require_next_step(sid, result)

    def resume(self, session_id: str, answer: dict[str, Any]) -> NextStep:
        config = {"configurable": {"thread_id": session_id}}
        result = self._graph.invoke(Command(resume=answer), config)
        return self._require_next_step(session_id, result)

    def current(self, session_id: str) -> NextStep | None:
        config = {"configurable": {"thread_id": session_id}}
        snap = self._graph.get_state(config)
        if snap.values is None:
            return None
        state = (
            snap.values
            if isinstance(snap.values, SessionState)
            else SessionState.model_validate(snap.values)
        )
        return next_step_from_state(state)

    def _require_next_step(self, session_id: str, result: Any) -> NextStep:
        if isinstance(result, dict) and "__interrupt__" in result:
            interrupts = result["__interrupt__"]
            if interrupts:
                return NextStep.model_validate(interrupts[0].value)

        # Complete / mid-await both live in the checkpoint — next_step_from_state
        # already handles is_session_complete. Do not re-parse invoke `result`
        # for that flag (duplicate of current(); silent desync risk under Postgres).
        step = self.current(session_id)
        if step is not None:
            return step

        raise RuntimeError(
            f"Graph finished for session {session_id} but checkpoint has no "
            "complete/pending state — possible checkpointer desync"
        )
