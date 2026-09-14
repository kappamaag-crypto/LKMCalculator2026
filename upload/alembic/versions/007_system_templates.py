"""Persist explicitly confirmed System Templates with source provenance."""
from alembic import op
import sqlalchemy as sa

revision = "007_system_templates"
down_revision = "006_engineering_book_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("manufacturer", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("substrate", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("source_path", sa.String(length=1000), nullable=False),
        sa.Column("source_sheet", sa.String(length=300), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="CONFIRMED"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "source_path", "source_sheet", "source_row", "source_sha256",
            name="uq_system_template_source",
        ),
    )
    op.create_index("ix_system_templates_name", "system_templates", ["name"])

    op.create_table(
        "system_template_layers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("layer_number", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("material_name", sa.String(length=300), nullable=False),
        sa.Column("dft_min", sa.Float(), nullable=True),
        sa.Column("dft_target", sa.Float(), nullable=True),
        sa.Column("dft_max", sa.Float(), nullable=True),
        sa.Column("source_path", sa.String(length=1000), nullable=False),
        sa.Column("source_sheet", sa.String(length=300), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["system_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("template_id", "layer_number", name="uq_system_template_layer_number"),
    )


def downgrade() -> None:
    op.drop_table("system_template_layers")
    op.drop_index("ix_system_templates_name", table_name="system_templates")
    op.drop_table("system_templates")
