"""Allow calculation costs to be unknown (NULL) in history.

Physical consumption remains stored normally; missing prices must not be encoded as zero.
"""

from alembic import op
import sqlalchemy as sa

revision = "003_nullable_calculation_costs"
down_revision = "002_nullable_material_properties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("calculations", schema=None) as batch_op:
        batch_op.alter_column("total_cost_per_m2", existing_type=sa.Float(), nullable=True)
        batch_op.alter_column("total_cost", existing_type=sa.Float(), nullable=True)
    with op.batch_alter_table("calculation_layers", schema=None) as batch_op:
        batch_op.alter_column("cost_per_m2", existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    # Do not invent zero prices for historical calculations.
    pass
