"""Keep unknown material thinner name as NULL instead of an empty-string default."""
from alembic import op
import sqlalchemy as sa

revision = "010_nullable_material_thinner_name"
down_revision = "009_nullable_material_thinner_required"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.alter_column(
            "thinner_name",
            existing_type=sa.String(length=200),
            nullable=True,
            existing_nullable=False,
            existing_server_default=sa.text("''"),
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.alter_column(
            "thinner_name",
            existing_type=sa.String(length=200),
            nullable=False,
            existing_nullable=True,
            server_default=sa.text("''"),
        )
