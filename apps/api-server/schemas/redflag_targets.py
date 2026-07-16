"""Red-flag subcategory row for Devise pool (closed 6-label set)."""
from __future__ import annotations

from pydantic import BaseModel

from schemas.literals import RedFlagSubcategory


class RedFlagTarget(BaseModel):
    """One always-eligible redflag_screening pool entry."""

    subcategory: RedFlagSubcategory
    clinical_hint: str
