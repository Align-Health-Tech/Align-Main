"""Shared types for the body diagram catalogue package.

``Side`` / ``Surface`` / ``SexVariant`` live in ``schemas.literals``.
"""
from __future__ import annotations

from pydantic import BaseModel

from schemas.literals import Side, Surface, SexVariant


class PrefillMapping(BaseModel):
    body_part: str  # classifier controlled vocabulary, e.g. "wrist"
    side: Side
    surface: Surface
    sex_variant: SexVariant

    diagram_file: str
    region_id: str


class RegionCoding(BaseModel):
    region_id: str  # UNIQUE across the whole catalogue
    layman_term: str
    anatomical_term: str
    fhir_system: str
    fhir_code: str  # TODO: placeholder throughout — needs real SNOMED CT lookup
    side: Side
