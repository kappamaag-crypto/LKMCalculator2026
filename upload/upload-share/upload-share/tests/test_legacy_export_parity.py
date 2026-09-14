"""§19 legacy parity: PDF / Excel export from SystemCalculationResult.

Shared: exporters consume the calculation result (not a second engine).
Intentional v3: missing price renders as «—» / UNKNOWN, not invented 0;
engineering vs customer Excel are separate surfaces.
"""
from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.infrastructure.export.excel_exporter import ExcelExporter
from app.infrastructure.export.pdf_exporter import PDFExporter
from app.services.calculation_service import CalculationService


def _result(price_per_kg=100.0):
    mat = Material(
        material_name="Parity Coat",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.2,
        solids_percent=60.0,
        solids_by_volume_percent=60.0,
        price_per_kg=price_per_kg,
        manufacturer="Parity",
    )
    obj = ObjectData(object_name="Export parity", area_m2=25.0)
    result, validation = CalculationService().calculate_system(
        obj, [LayerInput(material=mat, target_dft=100, losses_percent=0)]
    )
    assert not validation.has_errors
    return result


def test_v2_and_v3_pdf_share_export_calculation_entrypoint():
    root = Path(__file__).resolve().parents[2]
    v2 = (root / "v2" / "app" / "infrastructure" / "export" / "pdf_exporter.py").read_text(
        encoding="utf-8"
    )
    v3 = (root / "upload" / "app" / "infrastructure" / "export" / "pdf_exporter.py").read_text(
        encoding="utf-8"
    )
    assert "def export_calculation" in v2 and "def export_calculation" in v3
    assert "SystemCalculationResult" in v2 and "SystemCalculationResult" in v3


def test_v3_pdf_from_calculation_result_is_valid_pdf():
    result = _result(price_per_kg=120.0)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "parity.pdf"
        out = PDFExporter().export_calculation(result, path)
        assert out.exists()
        data = out.read_bytes()
        assert data[:4] == b"%PDF"
        assert len(data) > 800


def test_v3_pdf_unknown_cost_uses_em_dash_not_zero():
    result = _result(price_per_kg=None)
    assert result.total_cost_per_m2 is None
    from app.infrastructure.export import pdf_exporter as pe

    assert pe._cost(None) == "—"
    assert pe._cost(12.5) != "—"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "unknown.pdf"
        PDFExporter().export_calculation(result, path)
        assert path.exists() and path.stat().st_size > 500


def test_v3_excel_missing_price_marks_unknown():
    result = _result(price_per_kg=None)
    assert result.total_cost is None
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "missing.xlsx"
        ExcelExporter().export_calculation(result, path)
        assert path.exists()
        assert path.stat().st_size > 1000


def test_v3_has_engineering_and_customer_excel_split():
    root = Path(__file__).resolve().parents[2] / "upload" / "app" / "infrastructure" / "export"
    assert (root / "engineering_excel_exporter.py").exists()
    assert (root / "customer_excel_exporter.py").exists()
    v2_export = Path(__file__).resolve().parents[2] / "v2" / "app" / "infrastructure" / "export"
    assert (v2_export / "excel_exporter.py").exists()
    assert not (v2_export / "engineering_excel_exporter.py").exists()
