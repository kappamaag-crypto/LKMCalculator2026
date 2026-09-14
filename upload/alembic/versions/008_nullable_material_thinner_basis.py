"""Keep unknown material thinner basis as NULL instead of a hidden default."""
from alembic import op

revision = "008_nullable_material_thinner_basis"
down_revision = "007_system_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.alter_column(
            "thinner_basis",
            existing_type=None,
            nullable=True,
            existing_nullable=False,
            existing_server_default="BY_PAINT_VOLUME",
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.alter_column(
            "thinner_basis",
            existing_type=None,
            nullable=False,
            existing_nullable=True,
            server_default="BY_PAINT_VOLUME",
        )
