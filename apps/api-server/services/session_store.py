"""In-memory session / org store for M6 router lifecycle.

M7 will replace this with Postgres + RLS. Do not treat records here as
durable Encounter / Consent / SurveyResponse rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4

from engine.runner import SessionRunner
from schemas.literals import EncounterStatus, SegmentType

# Seeded default org for POST /sessions (QR → org binding deferred).
DEFAULT_ORG_ID = "org-urgent-care-demo"


@dataclass
class OrgRecord:
    id: str
    segment_type: SegmentType
    survey_enabled: bool = True


@dataclass
class SessionRecord:
    id: str
    patient_id: str
    organization_id: str
    status: EncounterStatus
    session_language: str = "en"
    patient_sex: Optional[str] = None
    # Stub Consent rows (M7: persist to Consent table).
    consents: list[dict[str, Any]] = field(default_factory=list)
    # True after graph complete while survey still outstanding (status stays IN_PROGRESS).
    awaiting_survey: bool = False
    # Stub SurveyResponse (M7: persist to SurveyResponse table).
    survey_response: Optional[dict[str, Any]] = None


class SessionStore:
    """Process-local dict store. One SessionRunner per segment_type (thread_id = session id)."""

    def __init__(self) -> None:
        self.orgs: dict[str, OrgRecord] = {}
        self.sessions: dict[str, SessionRecord] = {}
        self._runners: dict[str, SessionRunner] = {}
        self._seed_default_org()

    def reset(self) -> None:
        """Test / CLI helper — clear sessions; re-seed default org."""
        self.orgs.clear()
        self.sessions.clear()
        self._runners.clear()
        self._seed_default_org()

    def _seed_default_org(self) -> None:
        self.orgs[DEFAULT_ORG_ID] = OrgRecord(
            id=DEFAULT_ORG_ID,
            segment_type="URGENT_CARE",
            survey_enabled=True,
        )

    def ensure_org(
        self,
        *,
        organization_id: str,
        segment_type: SegmentType,
        survey_enabled: bool = True,
    ) -> OrgRecord:
        org = OrgRecord(
            id=organization_id,
            segment_type=segment_type,
            survey_enabled=survey_enabled,
        )
        self.orgs[organization_id] = org
        return org

    def get_org(self, organization_id: str) -> OrgRecord:
        org = self.orgs.get(organization_id)
        if org is None:
            raise KeyError(f"unknown organization: {organization_id}")
        return org

    def create_session_record(
        self,
        *,
        organization_id: str = DEFAULT_ORG_ID,
        session_language: str = "en",
        patient_sex: Optional[str] = None,
        session_id: Optional[str] = None,
        patient_id: Optional[str] = None,
    ) -> SessionRecord:
        if organization_id not in self.orgs:
            raise KeyError(f"unknown organization: {organization_id}")
        record = SessionRecord(
            id=session_id or str(uuid4()),
            patient_id=patient_id or str(uuid4()),
            organization_id=organization_id,
            status="NOT_STARTED",
            session_language=session_language,
            patient_sex=patient_sex,
        )
        self.sessions[record.id] = record
        return record

    def get_session(self, session_id: str) -> SessionRecord:
        record = self.sessions.get(session_id)
        if record is None:
            raise KeyError(f"unknown session: {session_id}")
        return record

    def runner_for(self, segment_type: SegmentType) -> SessionRunner:
        if segment_type not in self._runners:
            self._runners[segment_type] = SessionRunner(segment_type=segment_type)
        return self._runners[segment_type]


# Process singleton used by routers / CLI (tests call reset()).
store = SessionStore()
