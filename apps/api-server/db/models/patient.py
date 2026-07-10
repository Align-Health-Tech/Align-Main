"""Patient — FHIR: Patient. See docs/database/DATABASE.md."""
import uuid
from datetime import date, datetime
from typing import Literal

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

PatientKind = Literal["GUEST", "REGISTERED", "DEMO"]


class Patient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "patients"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    kind: Mapped[PatientKind] = mapped_column(String, nullable=False, default="GUEST")
    given_name: Mapped[str | None] = mapped_column(String, nullable=True)
    family_name: Mapped[str | None] = mapped_column(String, nullable=True)
    name_prefix: Mapped[str | None] = mapped_column(String, nullable=True)
    nhi_number: Mapped[str | None] = mapped_column(String(7), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    # FHIR extension — export under extension[], not Patient.gender.
    sex_at_birth: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String, nullable=False, default="en")
    ethnicity: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String, nullable=True)
    gms_status: Mapped[str | None] = mapped_column(String, nullable=True)
    # Free text, not an FK — registered GP is often at another org.
    registered_gp_name: Mapped[str | None] = mapped_column(String, nullable=True)
    registered_gp_practice: Mapped[str | None] = mapped_column(String, nullable=True)
    external_pms_patient_id: Mapped[str | None] = mapped_column(String, nullable=True)
    pms_vendor: Mapped[str | None] = mapped_column(String, nullable=True)
    pms_extension: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    contacts: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    addresses: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Patient id={self.id} kind={self.kind}>"
