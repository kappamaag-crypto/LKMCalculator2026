from pathlib import Path

from openpyxl import load_workbook

from app.domain.models import Material, ObjectData, CoatingSystem, LayerResult, SystemCalculationResult
from app.infrastructure.export.excel_exporter import ExcelExporter
from app.domain.enums import BinderType, MaterialType


def _historical_result():
    material = Material(
        id=101,
        manufacturer="Test",
        brand="Historical",
        material_name="Material v1",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.42,
        solids_by_volume_percent=64.0,
        price_per_kg=650.0,
    )
    layer = LayerResult(
        material=material,
        target_dft=120.0,
        losses_percent=5.0,
        wft=187.5,
        practical_consumption_kg=0.267,
        practical_consumption_l=0.188,
        cost_per_m2=173.55,
        total_consumption_kg=0.267,
        total_consumption_l=0.188,
        total_cost=173.55,
    )
    return SystemCalculationResult(
        system=CoatingSystem(system_name="Historical system"),
        object_data=ObjectData(object_name="Object", area_m2=100.0),
        layers=[layer],
        total_dft=120.0,
        total_practical_consumption_kg=0.267,
        total_practical_consumption_l=0.188,
        total_cost_per_m2=173.55,
        total_cost=17355.0,
    )


def test_excel_export_uses_result_snapshot_material_values(tmp_path: Path):
    path = tmp_path / "historical.xlsx"
    result = _historical_result()

    # Simulate a changed catalog: export receives the immutable calculation result,
    # so it must not query or substitute the current material row.
    changed_catalog_material = Material(
        id=101,
        material_name="Material v2",
        density=1.90,
        solids_by_volume_percent=48.0,
        price_per_kg=900.0,
    )
    assert changed_catalog_material.density != result.layers[0].material.density

    ExcelExporter().export_calculation(result, path)
    wb = load_workbook(path, data_only=True)

    materials = wb["Материалы"]
    assert materials.cell(4, 1).value == "Material v1"
    assert materials.cell(4, 3).value == 1.42
    assert materials.cell(4, 4).value == 64.0
    assert materials.cell(4, 5).value == 650.0
