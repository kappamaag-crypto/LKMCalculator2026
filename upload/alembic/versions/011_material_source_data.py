"""Persist full Excel provenance and raw technical observations for materials."""
from alembic import op
import sqlalchemy as sa

revision = "011_material_source_data"
down_revision = "010_nullable_material_thinner_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.add_column(
            sa.Column("source_data_json", sa.Text(), nullable=False, server_default="{}")
        )
        batch_op.alter_column("source_data_json", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.drop_column("source_data_json")
