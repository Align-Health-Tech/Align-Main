"""Survey + SurveyResponse. Internal (no FHIR). See docs/database/DATABASE.md."""
import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Survey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "surveys"
    __table_args__ = (UniqueConstraint("organization_id", "key", "version"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # `schema` clashes with SQLAlchemy's schema concept.
    schema_: Mapped[dict] = mapped_column("schema", JSONB, nullable=False)

    def __repr__(self) -> str:
        return f"<Survey id={self.id} key={self.key!r} version={self.version}>"


class SurveyResponse(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "survey_responses"
    __table_args__ = (UniqueConstraint("encounter_id", "survey_id"),)

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveys.id"), nullable=False, index=True
    )
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False)

    def __repr__(self) -> str:
        return f"<SurveyResponse id={self.id} survey_id={self.survey_id}>"
