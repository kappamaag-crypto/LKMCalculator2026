"""Тесты Excel-экспорта."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from app.domain.models import Material, ObjectData
from app.domain.enums import MaterialType, BinderType, CorrosionCategory, DurabilityLevel
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService

openpyxl = pytest.importorskip("openpyxl")
from openpyxl import load_workbook
from app.infrastructure.export.excel_exporter import ExcelExporter


@pytest.fixture
def sample_result():
    primer = Material(
        material_name="\u0413\u0440\u0443\u043d\u0442-\u042d\u043c\u0430\u043b\u044c Blank Universal",
        material_type=MaterialType.PRIMER_ENAMEL, binder_type=BinderType.EPOXY,
        density=1.4, solids_percent=73.0, price_per_kg=552.0, packaging_kg=20.0, manufacturer="Blank",
    )
    finish = Material(
        material_name="\u042d\u043c\u0430\u043b\u044c Blank Finish",
        material_type=MaterialType.FINISH, binder_type=BinderType.POLYURETHANE,
        density=1.3, solids_percent=58.0, price_per_kg=892.0, packaging_kg=20.0, manufacturer="Blank",
    )
    obj = ObjectData(
        object_name="\u0422\u0435\u0441\u0442", customer="\u0417\u0430\u043a\u0430\u0437\u0447\u0438\u043a",
        area_m2=100.0, calculation_number="T-001",
        corrosion_category=CorrosionCategory.C4, durability=DurabilityLevel.HIGH,
    )
    result, validation = CalculationService().calculate_system(
        obj, [LayerInput(material=primer, target_dft=200), LayerInput(material=finish, target_dft=100)]
    )
    assert not validation.has_errors
    return result


def test_export_creates_file(sample_result):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        ExcelExporter().export_calculation(sample_result, path)
        assert path.exists()
        assert path.stat().st_size > 1000


def test_export_has_required_sheets(sample_result):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        ExcelExporter().export_calculation(sample_result, path)
        wb = load_workbook(path)
        names = set(wb.sheetnames)
        assert "\u0418\u0441\u0445\u043e\u0434\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435" in names
        assert "\u0421\u043b\u043e\u0438" in names
        assert "\u041c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b" in names or "\u0418\u0442\u043e\u0433\u0438" in names
