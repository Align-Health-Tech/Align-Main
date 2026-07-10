"""Practitioner + PractitionerComment. See docs/database/DATABASE.md."""
import uuid
from typing import Literal

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

PractitionerRole = Literal["DOCTOR", "NURSE", "GP", "PHYSICIAN", "RECEPTIONIST"]


class Practitioner(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "practitioners"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    role: Mapped[PractitionerRole] = mapped_column(String, nullable=False)
    # NZ HPI Common Person Number (NNXXXX).
    hpi_cpn: Mapped[str | None] = mapped_column(String(6), nullable=True)

    def __repr__(self) -> str:
        return f"<Practitioner id={self.id} role={self.role}>"


class PractitionerComment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "practitioner_comments"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    practitioner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("practitioners.id"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<PractitionerComment id={self.id} encounter_id={self.encounter_id}>"
