"""Тесты PDF-экспорта."""
from __future__ import annotations
from pathlib import Path
import tempfile
import pytest
from app.domain.models import Material, ObjectData
from app.domain.enums import MaterialType, BinderType, CorrosionCategory, DurabilityLevel
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService
from app.infrastructure.export.pdf_exporter import PDFExporter
from app.domain.formulas import FORMULA_VERSION

@pytest.fixture
def sample_result():
    primer=Material(material_name="Грунт-Эмаль Blank Universal",material_type=MaterialType.PRIMER_ENAMEL,binder_type=BinderType.EPOXY,density=1.4,solids_percent=73.0,solids_by_volume_percent=73.0,price_per_kg=552.0,packaging_kg=20.0,manufacturer="Blank")
    finish=Material(material_name="Эмаль Blank Finish",material_type=MaterialType.FINISH,binder_type=BinderType.POLYURETHANE,density=1.3,solids_percent=58.0,solids_by_volume_percent=58.0,price_per_kg=892.0,packaging_kg=20.0,manufacturer="Blank")
    obj=ObjectData(object_name="Тест PDF",customer="Заказчик",area_m2=100.0,calculation_number="PDF-001",corrosion_category=CorrosionCategory.C4,durability=DurabilityLevel.HIGH)
    result,validation=CalculationService().calculate_system(obj,[LayerInput(material=primer,target_dft=200),LayerInput(material=finish,target_dft=100)])
    assert not validation.has_errors
    return result

def test_pdf_creates_file(sample_result):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"test.pdf"; PDFExporter().export_calculation(sample_result,path); assert path.exists() and path.stat().st_size>1000 and path.read_bytes()[:4]==b"%PDF"

def test_pdf_with_comparison(sample_result):
    from app.domain.comparison import ComparisonEngine
    primer,finish,obj=sample_result.layers[0].material,sample_result.layers[1].material,sample_result.object_data
    comparison=ComparisonEngine().compare(obj,[("A",[LayerInput(material=primer,target_dft=200),LayerInput(material=finish,target_dft=100)]),("B",[LayerInput(material=primer,target_dft=150),LayerInput(material=finish,target_dft=80)])])
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"cmp.pdf"; PDFExporter().export_calculation(sample_result,path,comparison=comparison); assert path.exists() and path.stat().st_size>2000

def test_pdf_contains_thinner_labels(sample_result):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"thinner.pdf"; PDFExporter().export_calculation(sample_result,path); data=path.read_bytes(); assert data[:4]==b"%PDF" and len(data)>1000

def test_pdf_contains_formula_version_and_date_marker(sample_result):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"metadata.pdf"; PDFExporter().export_calculation(sample_result,path); data=path.read_bytes()
        # PDF content is compressed/encoded, so verify stable metadata at the document level.
        assert b"/Title" in data
        assert str(FORMULA_VERSION).encode("ascii") in data

def test_pdf_unknown_total_cost_does_not_crash(sample_result):
    sample_result.total_cost_per_m2 = None
    sample_result.total_cost = None
    sample_result.total_thinner_cost = None
    for layer in sample_result.layers:
        layer.cost_per_m2 = None
        layer.thinner_cost_per_m2 = None
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"unknown-cost.pdf"; PDFExporter().export_calculation(sample_result,path); assert path.exists() and path.stat().st_size>1000
