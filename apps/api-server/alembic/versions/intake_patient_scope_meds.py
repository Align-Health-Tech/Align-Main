"""Patient-scope intake_fact_items; encounter_medication + pregnancy_possible.

Revision ID: intake_patient_scope_meds_001
Revises: summary_str_laterality_ck_001

- intake_fact_items.patient_id NOT NULL (backfilled from encounter)
- intake_fact_items.encounter_id nullable (provenance only)
- RLS: patient-linkage policy (mirrors patients §2), not direct encounter_id
- encounters.encounter_medication jsonb, encounters.pregnancy_possible bool
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "intake_patient_scope_meds_001"
down_revision: Union[str, None] = "summary_str_laterality_ck_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Encounter visit-scoped columns ---
    op.add_column(
        "encounters",
        sa.Column(
            "encounter_medication",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "encounters",
        sa.Column("pregnancy_possible", sa.Boolean(), nullable=True),
    )

    # --- intake_fact_items: patient_id primary scope ---
    op.add_column(
        "intake_fact_items",
        sa.Column("patient_id", sa.UUID(), nullable=True),
    )
    op.execute(
        """
        UPDATE intake_fact_items AS i
        SET patient_id = e.patient_id
        FROM encounters AS e
        WHERE i.encounter_id = e.id
        """
    )
    # Any orphan rows (should not exist) — fail loudly rather than invent patients.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM intake_fact_items WHERE patient_id IS NULL) THEN
            RAISE EXCEPTION
              'intake_fact_items backfill: rows with NULL patient_id remain';
          END IF;
        END $$;
        """
    )
    op.alter_column(
        "intake_fact_items",
        "patient_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_intake_fact_items_patient_id_patients",
        "intake_fact_items",
        "patients",
        ["patient_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_intake_fact_items_patient_id"),
        "intake_fact_items",
        ["patient_id"],
        unique=False,
    )
    op.alter_column(
        "intake_fact_items",
        "encounter_id",
        existing_type=sa.UUID(),
        nullable=True,
    )

    # --- RLS: drop encounter-scoped policy; add patient-linkage (patients §2 shape) ---
    op.execute("DROP POLICY IF EXISTS tenant_isolation_patient ON intake_fact_items;")
    op.execute("DROP POLICY IF EXISTS admin_read ON intake_fact_items;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_patient ON intake_fact_items TO align_app
        USING (
          organization_id = app.current_organization_id()
          AND (NOT app.is_patient() OR patient_id = (
            SELECT patient_id FROM encounters WHERE id = app.current_encounter_id()
          ))
        )
        WITH CHECK (
          organization_id = app.current_organization_id()
          AND (NOT app.is_patient() OR patient_id = (
            SELECT patient_id FROM encounters WHERE id = app.current_encounter_id()
          ))
        );
        """
    )
    op.execute(
        """
        CREATE POLICY admin_read ON intake_fact_items FOR SELECT TO align_admin
        USING (true);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_patient ON intake_fact_items;")
    op.execute("DROP POLICY IF EXISTS admin_read ON intake_fact_items;")
    # Restore encounter-scoped policy (requires non-null encounter_id).
    op.execute(
        """
        UPDATE intake_fact_items
        SET encounter_id = (
          SELECT e.id FROM encounters e
          WHERE e.patient_id = intake_fact_items.patient_id
          ORDER BY e.created_at DESC
          LIMIT 1
        )
        WHERE encounter_id IS NULL;
        """
    )
    op.alter_column(
        "intake_fact_items",
        "encounter_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation_patient ON intake_fact_items TO align_app
        USING (
          organization_id = app.current_organization_id()
          AND (NOT app.is_patient() OR encounter_id = app.current_encounter_id())
        )
        WITH CHECK (
          organization_id = app.current_organization_id()
          AND (NOT app.is_patient() OR encounter_id = app.current_encounter_id())
        );
        """
    )
    op.execute(
        """
        CREATE POLICY admin_read ON intake_fact_items FOR SELECT TO align_admin
        USING (true);
        """
    )

    op.drop_index(op.f("ix_intake_fact_items_patient_id"), table_name="intake_fact_items")
    op.drop_constraint(
        "fk_intake_fact_items_patient_id_patients",
        "intake_fact_items",
        type_="foreignkey",
    )
    op.drop_column("intake_fact_items", "patient_id")

    op.drop_column("encounters", "pregnancy_possible")
    op.drop_column("encounters", "encounter_medication")
