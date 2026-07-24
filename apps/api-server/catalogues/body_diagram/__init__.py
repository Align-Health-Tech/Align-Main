"""Body diagram catalogue — classifier vocab ↔ SVG region_id / CodedField.

Package layout splits region tables by diagram family; this module re-exports
the same public API as the former single-file catalogue so existing imports
(`from catalogues.body_diagram import resolve_prefill_candidates`,
…) keep working unchanged.

Two tables (not one): PREFILL_MAPPINGS allows duplicate region_ids across
front/back views; REGION_CODINGS is unique per region_id → CodedField.
fhir_code values are TODO placeholders (real SNOMED lookup required).
Deterministic — no LLM.
"""
from __future__ import annotations

from catalogues.body_diagram.resolvers import (
    DiagramPrefill,
    PREFILL_MAPPINGS,
    REGION_CODINGS,
    laterality_for_region_id,
    resolve_coding,
    resolve_prefill_candidates,
)
from catalogues.body_diagram.types import PrefillMapping, RegionCoding

__all__ = [
    "DiagramPrefill",
    "PREFILL_MAPPINGS",
    "PrefillMapping",
    "REGION_CODINGS",
    "RegionCoding",
    "laterality_for_region_id",
    "resolve_coding",
    "resolve_prefill_candidates",
]
