"""Encounter status machine: consent → graph → survey → AWAITING_REVIEW → COMPLETED.

M6: in-memory stubs for Consent / SurveyResponse / Encounter writes (see M7).
"""
from __future__ import annotations

from typing import Any, Optional

from engine.helpers.next_step import build_next_step, build_next_step_raw
from engine.runner import SessionRunner
from forms import (
    build_consent_questions,
    build_survey_questions,
)
from schemas.literals import EncounterStatus, SegmentType
from schemas.question_fields import NextStep
from schemas.session_states import SessionState
from services.session_errors import SessionConflictError, SessionNotFoundError
from services.session_store import DEFAULT_ORG_ID, SessionStore, store


class SessionLifecycle:
    def __init__(self, session_store: SessionStore | None = None) -> None:
        self._store = session_store or store

    def create_session(
        self,
        *,
        session_language: str = "en",
        patient_sex: Optional[str] = None,
        organization_id: str = DEFAULT_ORG_ID,
        segment_type: Optional[SegmentType] = None,
        survey_enabled: Optional[bool] = None,
    ) -> tuple[str, NextStep, EncounterStatus]:
        """POST /sessions — NOT_STARTED + consent NextStep (no graph)."""
        if segment_type is not None:
            # CLI / tests: ensure org exists with requested topology.
            self._store.ensure_org(
                organization_id=organization_id,
                segment_type=segment_type,
                survey_enabled=(
                    True if survey_enabled is None else survey_enabled
                ),
            )
        elif organization_id not in self._store.orgs:
            raise SessionNotFoundError(f"unknown organization: {organization_id}")

        record = self._store.create_session_record(
            organization_id=organization_id,
            session_language=session_language,
            patient_sex=patient_sex,
        )
        step = build_next_step_raw(
            0, build_consent_questions(), phase="consent"
        )
        return record.id, step, record.status

    def get_session(
        self, session_id: str
    ) -> tuple[NextStep, EncounterStatus]:
        """GET /sessions/{id} — rebuild current NextStep from status."""
        record = self._require_record(session_id)
        return self._next_step_for_record(record), record.status

    def respond(
        self, session_id: str, answer: dict[str, Any]
    ) -> tuple[NextStep, EncounterStatus]:
        """POST /sessions/{id}/respond — branch on status before graph."""
        record = self._require_record(session_id)

        if record.status == "NOT_STARTED":
            return self._respond_consent(record, answer)

        if record.status == "IN_PROGRESS" and record.awaiting_survey:
            return self._respond_survey(record, answer)

        if record.status == "IN_PROGRESS":
            return self._respond_graph(record, answer)

        if record.status in ("AWAITING_REVIEW", "COMPLETED"):
            raise SessionConflictError(
                f"session {session_id} is {record.status}; patient respond closed",
                status=record.status,
            )

        raise SessionConflictError(
            f"unexpected status {record.status}", status=record.status
        )

    def clinician_complete(
        self, session_id: str
    ) -> tuple[str, EncounterStatus]:
        """POST /clinician/sessions/{id}/complete."""
        record = self._require_record(session_id)
        if record.status != "AWAITING_REVIEW":
            raise SessionConflictError(
                "clinician complete requires AWAITING_REVIEW",
                status=record.status,
            )
        record.status = "COMPLETED"
        return record.id, record.status

    # ------------------------------------------------------------------
    # State readback (CLI debugging + clinician mirror)
    # ------------------------------------------------------------------

    def get_graph_state(self, session_id: str) -> SessionState | None:
        """Checkpointed SessionState, or None before the graph has started.

        Also backs the clinician mirror on the session responses, so the
        None-before-consent case is a normal path, not just a CLI edge.
        """
        record = self._store.sessions.get(session_id)
        if record is None or record.status == "NOT_STARTED":
            return None
        runner = self._runner_for_record(record)
        return self._load_state(runner, session_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _require_record(self, session_id: str):
        try:
            return self._store.get_session(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(str(exc)) from exc

    def _runner_for_record(self, record) -> SessionRunner:
        org = self._store.get_org(record.organization_id)
        return self._store.runner_for(org.segment_type)

    def _load_state(self, runner: SessionRunner, session_id: str) -> SessionState:
        snap = runner._graph.get_state(
            {"configurable": {"thread_id": session_id}}
        )
        values = snap.values
        if isinstance(values, SessionState):
            return values
        return SessionState.model_validate(values)

    def _next_step_for_record(self, record) -> NextStep:
        if record.status == "NOT_STARTED":
            return build_next_step_raw(
                0, build_consent_questions(), phase="consent"
            )
        if record.status == "IN_PROGRESS" and record.awaiting_survey:
            return self._survey_step(record)
        if record.status in ("AWAITING_REVIEW", "COMPLETED"):
            return self._patient_complete_step(record)
        runner = self._runner_for_record(record)
        step = runner.current(record.id)
        if step is None:
            raise SessionConflictError(
                f"no pending step for session {record.id}",
                status=record.status,
            )
        # Graph already complete but survey not yet presented (GET race).
        if step.step_type == "complete":
            return self._after_graph_complete(record, step)
        return step

    def _respond_consent(
        self, record, answer: dict[str, Any]
    ) -> tuple[NextStep, EncounterStatus]:
        if not _consent_accepted(answer):
            raise SessionConflictError(
                "consent not accepted", status=record.status
            )
        # Stub Consent row (M7: INSERT into Consent).
        record.consents.append(
            {
                "kind": "privacy",
                "version": "1",
                "accepted": True,
            }
        )
        record.status = "IN_PROGRESS"
        runner = self._runner_for_record(record)
        _sid, step = runner.start(
            session_id=record.id,
            patient_id=record.patient_id,
            organization_id=record.organization_id,
            session_language=record.session_language,
            patient_sex=record.patient_sex,
        )
        if step.step_type == "complete":
            return self._after_graph_complete(record, step), record.status
        return step, record.status

    def _respond_graph(
        self, record, answer: dict[str, Any]
    ) -> tuple[NextStep, EncounterStatus]:
        runner = self._runner_for_record(record)
        step = runner.resume(record.id, answer)
        if step.step_type == "complete":
            return self._after_graph_complete(record, step), record.status
        return step, record.status

    def _after_graph_complete(
        self, record, graph_complete: NextStep
    ) -> NextStep:
        """Intercept graph complete — survey (still IN_PROGRESS) or AWAITING_REVIEW."""
        org = self._store.get_org(record.organization_id)
        if org.survey_enabled and record.survey_response is None:
            record.awaiting_survey = True
            # Status stays IN_PROGRESS per ROUTER_SPEC.
            return self._survey_step(record)
        record.awaiting_survey = False
        record.status = "AWAITING_REVIEW"
        return self._patient_complete_step(record, turn=graph_complete.turn_number)

    def _survey_step(self, record) -> NextStep:
        runner = self._runner_for_record(record)
        state = self._load_state(runner, record.id)
        return build_next_step(
            state, build_survey_questions(), phase="survey"
        )

    def _respond_survey(
        self, record, answer: dict[str, Any]
    ) -> tuple[NextStep, EncounterStatus]:
        # Stub SurveyResponse (M7: INSERT into SurveyResponse).
        record.survey_response = {"answer": answer}
        record.awaiting_survey = False
        record.status = "AWAITING_REVIEW"
        return self._patient_complete_step(record), record.status

    def _patient_complete_step(
        self, record, *, turn: int | None = None
    ) -> NextStep:
        turn_number = turn
        if turn_number is None:
            try:
                runner = self._runner_for_record(record)
                state = self._load_state(runner, record.id)
                turn_number = state.turn_number
            except Exception:  # noqa: BLE001 — pre-graph edge
                turn_number = 0
        # phase="complete", not the last phase walked. This step is terminal, so
        # reporting "ice" here made the clinician header keep showing "Ice" after
        # the patient had finished.
        return NextStep(
            step_type="complete",
            phase="complete",
            turn_number=turn_number,
        )


def _consent_accepted(answer: dict[str, Any]) -> bool:
    """Accept common consent answer shapes."""
    if answer.get("accepted") is True:
        return True
    if answer.get("skip") is True:
        return False
    answers = answer.get("answers")
    if not isinstance(answers, list):
        return False
    for item in answers:
        if not isinstance(item, dict):
            continue
        qid = item.get("question_id")
        val = item.get("value")
        if qid in ("consent_privacy", "consent_accept") and val in (
            True,
            "true",
            "yes",
            "accept",
            "accepted",
        ):
            return True
    return False


# Process singleton for routers / CLI.
lifecycle = SessionLifecycle()
