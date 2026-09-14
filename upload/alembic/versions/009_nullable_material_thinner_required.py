"""Keep unknown material thinner requirement as NULL instead of a hidden default."""
from alembic import op
import sqlalchemy as sa

revision = "009_nullable_material_thinner_required"
down_revision = "008_nullable_material_thinner_basis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.alter_column(
            "thinner_required",
            existing_type=sa.Boolean(),
            nullable=True,
            existing_nullable=False,
            existing_server_default=sa.false(),
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.alter_column(
            "thinner_required",
            existing_type=sa.Boolean(),
            nullable=False,
            existing_nullable=True,
            server_default=sa.false(),
        )
