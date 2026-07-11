"""
PMSProvider — no LLM involvement at all. Plain data fetch/push, gated
per-organization by `organizations.pms_config.vendor`.
"""
from typing import Optional, Protocol

from pydantic import BaseModel


class PatientRecord(BaseModel):
    """What a real PMS returns for a patient lookup — shape is provisional
    until MedTechAdapter is actually built against the real API."""
    external_id: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    nhi_number: Optional[str] = None
    dob: Optional[str] = None


class ConsultSummary(BaseModel):
    """What gets pushed back to a PMS after intake completes."""
    encounter_summary: str
    chief_complaint: str


class PMSProvider(Protocol):
    def fetch_patient(self, identifier: str) -> Optional[PatientRecord]:
        """Look up an existing patient by whatever identifier the PMS
        matches on (NHI, external ID, etc). None if no match."""
        ...

    def push_consult_summary(self, encounter_id: str, summary: ConsultSummary) -> bool:
        """Write the completed intake summary back to the PMS. True on success."""
        ...

    def is_available(self) -> bool:
        """Health check — used for circuit-breaker-style fallback if the
        PMS is down mid-session (intake must never block on this)."""
        ...