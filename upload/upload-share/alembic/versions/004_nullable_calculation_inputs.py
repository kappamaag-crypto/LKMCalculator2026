"""Allow unknown area and target DFT to remain NULL in persisted data.

Existing numeric values are preserved. This migration only relaxes NOT NULL
constraints; it does not convert zeroes to NULL because zero may be a legacy
explicit value and cannot be reclassified safely.
"""

from alembic import op
import sqlalchemy as sa

revision = "004_nullable_calculation_inputs"
down_revision = "003_nullable_calculation_costs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("coating_system_layers", schema=None) as batch_op:
        batch_op.alter_column(
            "target_dft",
            existing_type=sa.Float(),
            nullable=True,
        )

    with op.batch_alter_table("calculations", schema=None) as batch_op:
        batch_op.alter_column(
            "area_m2",
            existing_type=sa.Float(),
            nullable=True,
        )

    with op.batch_alter_table("calculation_layers", schema=None) as batch_op:
        batch_op.alter_column(
            "dry_thickness",
            existing_type=sa.Float(),
            nullable=True,
        )

    with op.batch_alter_table("comparisons", schema=None) as batch_op:
        batch_op.alter_column(
            "area_m2",
            existing_type=sa.Float(),
            nullable=True,
        )


def downgrade() -> None:
    # Do not invent DFT/area values for NULL historical records.
    pass
