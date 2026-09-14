"""v3 core schema: engineering fields, 2K components, packages and snapshots.

The migration is intentionally additive. Existing tables and rows are preserved.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "001_v3_core"
down_revision = None
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    if table not in inspect(bind).get_table_names():
        return
    columns = {c["name"] for c in inspect(bind).get_columns(table)}
    if column.name not in columns:
        op.add_column(table, column)


def upgrade() -> None:
    # Existing materials: additive engineering metadata.
    for column in [
        sa.Column("solids_by_volume_percent", sa.Float(), nullable=True),
        sa.Column("full_cure_time_h", sa.Float(), nullable=True),
        sa.Column("pot_life_h", sa.Float(), nullable=True),
        sa.Column("induction_time_min", sa.Float(), nullable=True),
        sa.Column("max_relative_humidity", sa.Float(), nullable=True),
        sa.Column("min_dew_point_margin_c", sa.Float(), nullable=True),
        sa.Column("thinner_basis", sa.String(length=40), nullable=True),
        sa.Column("is_two_component", sa.Boolean(), nullable=True),
        sa.Column("datasheet_version", sa.String(length=100), nullable=True),
        sa.Column("datasheet_date", sa.String(length=30), nullable=True),
        sa.Column("safety_data_sheet", sa.String(length=500), nullable=True),
        sa.Column("certificate_version", sa.String(length=100), nullable=True),
        sa.Column("test_protocol", sa.String(length=500), nullable=True),
    ]:
        _add_column_if_missing("materials", column)

    # Existing systems/layers.
    for column in [sa.Column("total_dft_target", sa.Float(), nullable=True)]:
        _add_column_if_missing("coating_systems", column)
    for column in [
        sa.Column("thinner_basis", sa.String(length=40), nullable=True),
        sa.Column("passes", sa.Integer(), nullable=True),
        sa.Column("application_method", sa.String(length=100), nullable=True),
    ]:
        _add_column_if_missing("coating_system_layers", column)

    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "material_components" not in tables:
        op.create_table(
            "material_components",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
            sa.Column("component_code", sa.String(length=10), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("density_kg_l", sa.Float(), nullable=True),
            sa.Column("price_per_kg", sa.Float(), nullable=True),
            sa.Column("price_per_liter", sa.Float(), nullable=True),
            sa.Column("packaging_kg", sa.Float(), nullable=True),
            sa.Column("packaging_l", sa.Float(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.UniqueConstraint("material_id", "component_code", name="uq_material_component_code"),
        )

    if "material_mixes" not in tables:
        op.create_table(
            "material_mixes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("mix_ratio_a", sa.Float(), nullable=False),
            sa.Column("mix_ratio_b", sa.Float(), nullable=False),
            sa.Column("ratio_basis", sa.String(length=20), nullable=False, server_default="mass"),
            sa.Column("working_time_minutes", sa.Float(), nullable=True),
            sa.Column("induction_time_minutes", sa.Float(), nullable=True),
            sa.Column("temperature_reference", sa.Float(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        )

    if "packages" not in tables:
        op.create_table(
            "packages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=True),
            sa.Column("component_id", sa.Integer(), sa.ForeignKey("material_components.id", ondelete="CASCADE"), nullable=True),
            sa.Column("package_name", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("net_weight_kg", sa.Float(), nullable=True),
            sa.Column("net_volume_l", sa.Float(), nullable=True),
            sa.Column("units_per_set", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("package_type", sa.String(length=30), nullable=False, server_default="single"),
            sa.Column("is_component_package", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    if "calculation_snapshots" not in tables:
        op.create_table(
            "calculation_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("calculation_id", sa.Integer(), sa.ForeignKey("calculations.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("project_name", sa.String(length=300), nullable=False, server_default=""),
            sa.Column("object_data_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("system_data_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("materials_data_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("formula_version", sa.String(length=30), nullable=False, server_default="3.0"),
            sa.Column("calculator_version", sa.String(length=30), nullable=False, server_default="3.0.0"),
            sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    # Deliberately non-destructive v3 migration: no automatic data deletion.
    pass
