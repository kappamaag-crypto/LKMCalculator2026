"""Allow unknown density and solids values to remain NULL.

This is a non-destructive migration: existing numeric values are preserved.
"""

from alembic import op
import sqlalchemy as sa

revision = "002_nullable_material_properties"
down_revision = "001_v3_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.alter_column(
            "density",
            existing_type=sa.Float(),
            nullable=True,
        )
        batch_op.alter_column(
            "solids_percent",
            existing_type=sa.Float(),
            nullable=True,
        )


def downgrade() -> None:
    # Existing NULL values cannot safely be converted to engineering defaults.
    # Keep downgrade non-destructive rather than inventing material data.
    pass
