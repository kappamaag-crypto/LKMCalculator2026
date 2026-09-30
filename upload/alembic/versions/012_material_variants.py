"""Add first-class RAL/color material variants and layer selection."""
from alembic import op
import sqlalchemy as sa

revision = "012_material_variants"
down_revision = "011_material_source_data"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "material_variants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ral", sa.String(50), nullable=False, server_default=""),
        sa.Column("color", sa.String(100), nullable=False, server_default=""),
        sa.Column("price_per_kg", sa.Float(), nullable=True),
        sa.Column("price_per_liter", sa.Float(), nullable=True),
        sa.Column("prices_include_vat", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("density", sa.Float(), nullable=True),
        sa.Column("solids_by_volume_percent", sa.Float(), nullable=True),
        sa.Column("recommended_dft_min", sa.Float(), nullable=True),
        sa.Column("recommended_dft_max", sa.Float(), nullable=True),
        sa.Column("source_data_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("material_id", "ral", "color", name="uq_material_variant_ral_color"),
    )
    op.create_index("ix_material_variants_material_id", "material_variants", ["material_id"])
    with op.batch_alter_table("coating_system_layers") as batch_op:
        batch_op.add_column(sa.Column("material_variant_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_coating_system_layers_material_variant_id", ["material_variant_id"])
        batch_op.create_foreign_key("fk_coating_system_layers_material_variant_id", "material_variants", ["material_variant_id"], ["id"], ondelete="SET NULL")

def downgrade() -> None:
    with op.batch_alter_table("coating_system_layers") as batch_op:
        batch_op.drop_constraint("fk_coating_system_layers_material_variant_id", type_="foreignkey")
        batch_op.drop_index("ix_coating_system_layers_material_variant_id")
        batch_op.drop_column("material_variant_id")
    op.drop_index("ix_material_variants_material_id", table_name="material_variants")
    op.drop_table("material_variants")
