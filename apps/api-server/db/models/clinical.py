"""BodyStructure, RadiationSite, Flag, IntakeFactItem. See docs/database/DATABASE.md."""
import uuid
from typing import Literal

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

FlagSource = Literal["CATALOGUE", "LILLY_INFERRED", "PRACTITIONER_ENTERED"]
FlagTier = Literal["MILD", "MODERATE", "SEVERE", "EXTREME"]
FlagStatus = Literal["ACTIVE", "INACTIVE", "ENTERED_IN_ERROR"]

IntakeFactKind = Literal[
    "ALLERGY",
    "MEDICATION",
    "CONDITION",
    "PROCEDURE",
    "IMMUNIZATION",
    "FAMILY_HISTORY",
    "SOCIAL_HISTORY",
    "VITAL_SIGN",
    "OTHER_OBSERVATION",
]
IntakeFactSource = Literal["PATIENT_INTAKE", "LILLY_EXTRACTED", "PRACTITIONER_ENTERED"]


class BodyStructure(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "body_structures"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    # Static lookup: {layman_term, anatomical_term, fhir_system, fhir_code}
    region_detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sub_region_detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    laterality: Mapped[str | None] = mapped_column(String, nullable=True)
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
    __tablename__ = "intake_fact_items"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    kind: Mapped[IntakeFactKind] = mapped_column(String, nullable=False)
    source: Mapped[IntakeFactSource] = mapped_column(String, nullable=False)
    fhir_system: Mapped[str | None] = mapped_column(String, nullable=True)
    fhir_code: Mapped[str | None] = mapped_column(String, nullable=True)
    fhir_display: Mapped[str | None] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<IntakeFactItem id={self.id} kind={self.kind}>"
