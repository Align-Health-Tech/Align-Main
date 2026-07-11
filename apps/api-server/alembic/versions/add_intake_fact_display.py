"""Add intake_fact_items.display (jsonb narrative, per DATABASE.md).

Revision ID: add_intake_fact_display_001
Revises: rls_roles_policies_001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "add_intake_fact_display_001"
down_revision: Union[str, None] = "rls_roles_policies_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "intake_fact_items",
        sa.Column("display", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("intake_fact_items", "display")
