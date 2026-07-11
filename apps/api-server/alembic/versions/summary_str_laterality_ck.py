"""encounter_summary → string; body_structures.laterality CHECK.

Revision ID: summary_str_laterality_ck_001
Revises: add_intake_fact_display_001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "summary_str_laterality_ck_001"
down_revision: Union[str, None] = "add_intake_fact_display_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "encounters",
        "encounter_summary",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.String(),
        existing_nullable=True,
        postgresql_using=(
            "CASE WHEN encounter_summary IS NULL THEN NULL "
            "WHEN jsonb_typeof(encounter_summary) = 'string' "
            "THEN encounter_summary #>> '{}' "
            "ELSE encounter_summary::text END"
        ),
    )
    op.create_check_constraint(
        "ck_body_structures_laterality",
        "body_structures",
        "laterality IS NULL OR laterality IN ('left', 'right', 'bilateral')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_body_structures_laterality", "body_structures", type_="check"
    )
    op.alter_column(
        "encounters",
        "encounter_summary",
        existing_type=sa.String(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
        postgresql_using=(
            "CASE WHEN encounter_summary IS NULL THEN NULL "
            "ELSE to_jsonb(encounter_summary::text) END"
        ),
    )
