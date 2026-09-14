"""§19 legacy parity: UI calculation workflow and systems editor (source contract).

Qt E2E is out of this file (sandbox often has no PySide6). Evidence here is the
public workflow surface in v2/v3 views plus v3 UNKNOWN-area contract.
Headless Qt smokes already exist: test_calculation_view_smoke.py, test_systems_view.py.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_v2_and_v3_calculation_views_share_workflow_surface():
    v2 = _read("v2/app/ui/views/calculation_view.py")
    v3 = _read("upload/app/ui/views/calculation_view.py")
    assert "class CalculationView" in v2 and "class CalculationView" in v3
    for name in (
        "set_materials",
        "_on_add_layer",
        "_on_remove_layer",
        "_on_clear_layers",
        "_build_object_data",
        "_on_calculate",
    ):
        assert f"def {name}" in v2, name
        assert f"def {name}" in v3, name
    assert "def _on_load_saved_system" in v3
    assert "def restore_snapshot" in v3
    assert "_area_unknown" in v3
    assert "btn_excel" in v3 and "btn_pdf" in v3


def test_v3_object_data_area_unknown_is_none_not_zero():
    src = _read("upload/app/ui/views/calculation_view.py")
    assert "area_m2=None if self._area_unknown else self.spin_area.value()" in src
    assert "def _on_area_changed" in src
    assert "self._area_unknown=False" in src


def test_v3_calculation_view_uses_calculation_service_not_excel_engine():
    src = _read("upload/app/ui/views/calculation_view.py")
    assert "CalculationService" in src
    assert "self.service.calculate_system" in src or "self.service.calculate" in src
    assert "EngineeringExcelExporter" in src or "_export_excel" in src
    assert "PdfExporter" in src or "_export_pdf" in src


def test_calculation_view_smoke_covers_direct_and_saved_system_paths():
    smoke = _read("upload/tests/test_calculation_view_smoke.py")
    assert "def test_calculation_view_calculates_and_enables_result_actions" in smoke
    assert "def test_calculation_view_loads_saved_system_into_editable_calculation" in smoke
    assert "btn_excel.isEnabled()" in smoke
    assert "load_system" in smoke or "set_systems" in smoke or "Сохранённая" in smoke


def test_v2_has_no_systems_editor_view():
    v2_views = ROOT / "v2" / "app" / "ui" / "views"
    names = [p.name for p in v2_views.glob("*.py")]
    assert "systems_view.py" not in names
    assert "calculation_view.py" in names


def test_v3_systems_editor_has_crud_and_compatibility_refresh():
    src = _read("upload/app/ui/views/systems_view.py")
    assert "class SystemsView" in src
    for name in ("_new", "_save", "_delete_system", "_add_layer", "_delete_layer", "_move_layer"):
        assert f"def {name}" in src, name
    assert "def _refresh_compatibility" in src
    assert "def set_calculation_result" in src
    assert "def _from_calculation" in src


def test_systems_view_smoke_exists():
    smoke = _read("upload/tests/test_systems_view.py")
    assert "SystemsView" in smoke
    assert "QApplication" in smoke
