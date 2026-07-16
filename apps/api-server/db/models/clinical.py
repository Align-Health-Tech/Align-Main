"""BodyStructure, RadiationSite, Flag, IntakeFactItem. See docs/database/DATABASE.md."""
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from schemas.literals import (
    FlagSource,
    FlagStatus,
    FlagTier,
    IntakeFactKind,
    IntakeFactSource,
    Laterality,
)


class BodyStructure(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "body_structures"
    __table_args__ = (
        CheckConstraint(
            "laterality IS NULL OR laterality IN ('left', 'right', 'bilateral')",
            name="ck_body_structures_laterality",
        ),
    )

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    # Static lookup: {layman_term, anatomical_term, fhir_system, fhir_code}
    region_detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sub_region_detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    laterality: Mapped[Laterality | None] = mapped_column(String, nullable=True)
    severity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    character: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    radiation_status: Mapped[str | None] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<BodyStructure id={self.id} encounter_id={self.encounter_id}>"


class RadiationSite(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "radiation_sites"

    body_structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("body_structures.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    region_detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<RadiationSite id={self.id} body_structure_id={self.body_structure_id}>"


class Flag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "flags"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    source: Mapped[FlagSource] = mapped_column(String, nullable=False)
    tier: Mapped[FlagTier] = mapped_column(String, nullable=False)
    status: Mapped[FlagStatus] = mapped_column(String, nullable=False, default="ACTIVE")
    fhir_system: Mapped[str | None] = mapped_column(String, nullable=True)
    fhir_code: Mapped[str | None] = mapped_column(String, nullable=True)
    fhir_display: Mapped[str | None] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Flag id={self.id} tier={self.tier} status={self.status}>"


class IntakeFactItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Patient-scoped persistent fact (allergies, usual meds, PMH, …).

    ``patient_id`` is the access scope. ``encounter_id`` is nullable provenance
    ("first noted in this encounter"). ``kind=MEDICATION`` means usual/ongoing
    meds — visit-symptom meds are ``Encounter.encounter_medication``.
    """

    __tablename__ = "intake_fact_items"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    # Nullable — first-noted provenance only; not the RLS scoping key.
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    kind: Mapped[IntakeFactKind] = mapped_column(String, nullable=False)
    source: Mapped[IntakeFactSource] = mapped_column(String, nullable=False)
    # jsonb: {text} or {text, en_text} — patient-stated fact; distinct from fhir_display
    display: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fhir_system: Mapped[str | None] = mapped_column(String, nullable=True)
    fhir_code: Mapped[str | None] = mapped_column(String, nullable=True)
    fhir_display: Mapped[str | None] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<IntakeFactItem id={self.id} kind={self.kind}>"
