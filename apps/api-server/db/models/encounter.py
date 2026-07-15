"""Encounter — FHIR: Encounter. `id` is also the LangGraph thread_id. See docs/database/DATABASE.md."""
import uuid
from typing import Literal

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

EncounterStatus = Literal["NOT_STARTED", "IN_PROGRESS", "AWAITING_REVIEW", "COMPLETED"]
PresentationCategory = Literal["LOCALISED", "NOT_LOCALISED"]


class Encounter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "encounters"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    status: Mapped[EncounterStatus] = mapped_column(
        String, nullable=False, default="NOT_STARTED"
    )
    presentation_category: Mapped[PresentationCategory | None] = mapped_column(
        String, nullable=True
    )
    # jsonb: {text, source} or {text, en_text, source};
    # source = "option"|"free_text"|"ai_summary"
    chief_complaint: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # jsonb: {text, source} or {text, en_text, source}; source = "option"|"free_text"
    duration: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    persistence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    progression: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    onset_circumstance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    self_management: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    severity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_change: Mapped[str | None] = mapped_column(String, nullable=True)
    functional_impact_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # jsonb array of {text, source} / {text, en_text, source}
    character: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    mitigating_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    exacerbating_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    comorbidities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ice_idea: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ice_concern: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ice_expectation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Plain English summary string — not a NarrativeField / jsonb wrapper.
    encounter_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    acc_claim_suspected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acc_can_work: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    def __repr__(self) -> str:
        return f"<Encounter id={self.id} status={self.status}>"
