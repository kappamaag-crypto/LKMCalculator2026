"""Тесты PDF-экспорта."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from app.domain.models import Material, ObjectData, CoatingSystem
from app.domain.enums import MaterialType, BinderType
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService

reportlab = pytest.importorskip("reportlab")
from app.infrastructure.export.pdf_exporter import PDFExporter


@pytest.fixture
def sample_result():
    primer = Material(
        material_name="\u0413\u0440\u0443\u043d\u0442 Test",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4, solids_percent=73.0, price_per_kg=552.0, packaging_kg=20.0,
    )
    obj = ObjectData(object_name="PDF Test", area_m2=100.0, calculation_number="PDF-001")
    result, val = CalculationService().calculate_system(
        obj, [LayerInput(material=primer, target_dft=200)]
    )
    assert not val.has_errors
    return result


def test_pdf_export_creates_file(sample_result):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.pdf"
        exporter = PDFExporter()
        exporter.export_calculation(sample_result, path)
        assert path.exists()
        assert path.stat().st_size > 500
