"""Drop unused Flag provenance and severity-tier columns.

Revision ID: simplify_flag_status_001
Revises: intake_patient_scope_meds_001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "simplify_flag_status_001"
down_revision: Union[str, None] = "intake_patient_scope_meds_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("flags", "source")
    op.drop_column("flags", "tier")


def downgrade() -> None:
    # Downgrade must populate legacy NOT NULL columns for any existing rows.
    op.add_column(
        "flags",
        sa.Column(
            "source",
            sa.String(),
            nullable=False,
            server_default="CATALOGUE",
        ),
    )
    op.add_column(
        "flags",
        sa.Column(
            "tier",
            sa.String(),
            nullable=False,
            server_default="SEVERE",
        ),
    )
    op.alter_column("flags", "source", server_default=None)
    op.alter_column("flags", "tier", server_default=None)
