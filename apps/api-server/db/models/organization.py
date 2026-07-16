"""Organization — FHIR: Organization. See docs/database/DATABASE.md."""
from typing import get_args

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from schemas.literals import SegmentType

# Only real Postgres ENUM in the schema — fixed three segments.
segment_type_enum = Enum(*get_args(SegmentType), name="segment_type_enum")


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    segment_type: Mapped[SegmentType] = mapped_column(segment_type_enum, nullable=False)
    pms_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Secrets — kept separate from pms_config identity info.
    pms_integration_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"
