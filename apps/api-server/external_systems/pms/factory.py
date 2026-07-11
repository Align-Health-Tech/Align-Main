"""
Picks the concrete PMSProvider for a given organization, based on
organizations.pms_config.vendor. See docs/database/DATABASE.md §organizations.
"""
from external_systems.pms.adapters import MedTechAdapter, NoPMSAdapter
from external_systems.pms.provider import PMSProvider


def get_pms_provider(pms_config: dict | None, pms_integration_config: dict | None) -> PMSProvider:
    vendor = (pms_config or {}).get("vendor")
    if vendor == "MEDTECH":
        return MedTechAdapter(credentials=pms_integration_config or {})
    return NoPMSAdapter()