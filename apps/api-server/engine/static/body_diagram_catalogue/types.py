"""Shared types for the body diagram catalogue package."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

Side = Literal["left", "right", "both", "midline", "unknown"]
Surface = Literal["front", "back", "inner", "outer", "unknown"]
SexVariant = Optional[Literal["male", "female"]]  # None = unisex diagram


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
