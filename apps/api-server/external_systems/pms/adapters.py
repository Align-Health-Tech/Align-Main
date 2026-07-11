"""
PMSProvider implementations. NoPMSAdapter is complete — it IS the "PMS off"
behavior, not a branch in engine code. MedTechAdapter is a stub until built
against the real API.
"""
from typing import Optional

from external_systems.pms.provider import ConsultSummary, PatientRecord, PMSProvider


class NoPMSAdapter(PMSProvider):
    """No PMS configured for this organization. Always succeeds, always
    reports available — intake must work identically whether or not a
    clinic has PMS integration turned on."""

    def fetch_patient(self, identifier: str) -> Optional[PatientRecord]:
        return None

    def push_consult_summary(self, encounter_id: str, summary: ConsultSummary) -> bool:
        return True

    def is_available(self) -> bool:
        return True


class MedTechAdapter(PMSProvider):
    """Not built yet. Raises deliberately rather than silently no-op'ing,
    so a misconfigured org (pms_config.vendor = "MEDTECH" but no real
    integration wired up) fails loudly instead of pretending to work."""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    def fetch_patient(self, identifier: str) -> Optional[PatientRecord]:
        raise NotImplementedError("MedTechAdapter.fetch_patient not yet implemented")

    def push_consult_summary(self, encounter_id: str, summary: ConsultSummary) -> bool:
        raise NotImplementedError("MedTechAdapter.push_consult_summary not yet implemented")

    def is_available(self) -> bool:
        return False