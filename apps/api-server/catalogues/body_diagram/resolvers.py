"""Prefill + coding resolvers over the combined catalogue lists."""
from __future__ import annotations

from typing import Optional, get_args

from pydantic import BaseModel

from catalogues.body_diagram.types import (
    PrefillMapping,
    RegionCoding,
    SexVariant,
)
from schemas.clinical_ai_io import LocalisedAnatomySite
from schemas.jsonb_fields import CodedField
from schemas.literals import Laterality, Side, Surface

from . import arms, face, legs_back, legs_front, torso_back, torso_front

_SIDES = frozenset(get_args(Side))
_SURFACES = frozenset(get_args(Surface))

PREFILL_MAPPINGS: list[PrefillMapping] = [
    *arms.PREFILL_MAPPINGS,
    *face.PREFILL_MAPPINGS,
    *legs_front.PREFILL_MAPPINGS,
    *legs_back.PREFILL_MAPPINGS,
    *torso_front.PREFILL_MAPPINGS,
    *torso_back.PREFILL_MAPPINGS,
]


def _dedupe_codings(rows: list[RegionCoding]) -> list[RegionCoding]:
    seen: set[str] = set()
    out: list[RegionCoding] = []
    for row in rows:
        if row.region_id in seen:
            continue
        seen.add(row.region_id)
        out.append(row)
    return out


REGION_CODINGS: list[RegionCoding] = _dedupe_codings(
    [
        *arms.REGION_CODINGS,
        *face.REGION_CODINGS,
        *legs_front.REGION_CODINGS,
        *legs_back.REGION_CODINGS,
        *torso_front.REGION_CODINGS,
        *torso_back.REGION_CODINGS,
    ]
)


class DiagramPrefill(BaseModel):
    diagram_file: str
    highlighted_region_ids: list[str]


def resolve_prefill_candidates(
    sites: list[LocalisedAnatomySite],
    patient_sex: Optional[str],
) -> Optional[DiagramPrefill]:
    """Multi-site prefill: converge on highest-confidence diagram, union region_ids.

    Convergence: pick diagram_file from the highest-confidence site that
    resolves; union region_ids from every other site that resolves to the
    *same* diagram_file; drop sites that map to a different sheet.
    """
    resolved: list[tuple[LocalisedAnatomySite, PrefillMapping]] = []
    for site in sites:
        if site.side not in _SIDES or site.surface not in _SURFACES:
            continue
        row = _resolve_prefill(
            body_part=site.body_part,
            side=site.side,  # type: ignore[arg-type]
            surface=site.surface,  # type: ignore[arg-type]
            patient_sex=patient_sex,
        )
        if row is not None:
            resolved.append((site, row))

    if not resolved:
        return None

    resolved.sort(key=lambda pair: float(pair[0].confidence), reverse=True)
    target_diagram = resolved[0][1].diagram_file

    region_ids = [
        row.region_id for _site, row in resolved if row.diagram_file == target_diagram
    ]
    seen: set[str] = set()
    unique_region_ids = [r for r in region_ids if not (r in seen or seen.add(r))]

    return DiagramPrefill(
        diagram_file=target_diagram, highlighted_region_ids=unique_region_ids
    )


def resolve_coding(region_id: str) -> Optional[CodedField]:
    """Map confirmed region_id → CodedField for body_structures.region_detail."""
    for row in REGION_CODINGS:
        if row.region_id == region_id:
            return CodedField(
                layman_term=row.layman_term,
                anatomical_term=row.anatomical_term,
                fhir_system=row.fhir_system,
                fhir_code=row.fhir_code,
            )
    return None


def laterality_for_region_id(region_id: str) -> Optional[Laterality]:
    """Derive body_structures.laterality from the catalogue side for region_id."""
    for row in REGION_CODINGS:
        if row.region_id != region_id:
            continue
        if row.side == "left":
            return "left"
        if row.side == "right":
            return "right"
        if row.side == "both":
            return "bilateral"
        return None
    return None


# ---------------------------------------------------------------------------
# Internal helpers (private, internal helper — not part of the public surface)
# See docs/repository-rule/REPOSITORYRULE.md
# ---------------------------------------------------------------------------


def _resolve_prefill(
    body_part: str,
    side: Side,
    surface: Surface,
    patient_sex: Optional[str],
) -> Optional[PrefillMapping]:
    """Single-site lookup — used by resolve_prefill_candidates().

    1. Exact match on body_part + side + surface + sex_variant.
    2. If surface is ``unknown`` and exact match fails, match body_part +
       side + sex_variant only (first PREFILL_MAPPINGS hit).
    3. Otherwise None.
    """
    sex_variant: SexVariant = (
        patient_sex if patient_sex in ("male", "female") else None
    )
    exact = _find_prefill(
        body_part=body_part,
        side=side,
        surface=surface,
        sex_variant=sex_variant,
        ignore_surface=False,
    )
    if exact is not None:
        return exact
    if surface == "unknown":
        return _find_prefill(
            body_part=body_part,
            side=side,
            surface=surface,
            sex_variant=sex_variant,
            ignore_surface=True,
        )
    return None


def _find_prefill(
    *,
    body_part: str,
    side: Side,
    surface: Surface,
    sex_variant: SexVariant,
    ignore_surface: bool,
) -> Optional[PrefillMapping]:
    for row in PREFILL_MAPPINGS:
        if row.body_part != body_part or row.side != side:
            continue
        if not ignore_surface and row.surface != surface:
            continue
        if row.sex_variant is not None and row.sex_variant != sex_variant:
            continue
        return row
    return None
