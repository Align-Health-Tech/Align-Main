"""
Public surface of the PMS provider module. Import from here, not from the
individual files — `from external_systems.pms import get_pms_provider`, not
`from external_systems.pms.factory import get_pms_provider`.

This set of code is still a skeleton and not implemented yet. Will be implemented once demo engine is built. 
"""
from external_systems.pms.adapters import MedTechAdapter, NoPMSAdapter
from external_systems.pms.factory import get_pms_provider
from external_systems.pms.provider import ConsultSummary, PatientRecord, PMSProvider

__all__ = [
    "PMSProvider",
    "PatientRecord",
    "ConsultSummary",
    "NoPMSAdapter",
    "MedTechAdapter",
    "get_pms_provider",
]