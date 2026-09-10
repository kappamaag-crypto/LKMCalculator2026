from PySide6.QtWidgets import QApplication, QMessageBox
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.engine import Base
from app.infrastructure.database.models import MaterialORM
import app.ui.dialogs.ad_hoc_material_dialog as dialog_module
from app.ui.dialogs.ad_hoc_material_dialog import AdHocMaterialDialog
from app.domain.enums import BinderType, MaterialType


def _qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _fill(dialog, *, name: str):
    dialog.ed_name.setText(name)
    dialog.ed_manufacturer.setText("ООО Тест")
    dialog.ed_brand.setText("Test Brand")
    dialog.cmb_type.setCurrentData(MaterialType.PRIMER)
    dialog.cmb_binder.setCurrentData(BinderType.EPOXY)
    dialog.chk_two_component.setChecked(True)
    dialog.spin_density.setValue(1.47)
    dialog.spin_solids.setValue(72.5)
    dialog.spin_price.setValue(845.30)
    dialog.spin_dft_min.setValue(80)
    dialog.spin_dft_max.setValue(160)
    dialog.spin_hard_max.setValue(200)


def test_normalize_name_collapses_whitespace_and_case():
    assert AdHocMaterialDialog._normalize_name("  Blank   Universal  ") == "blank universal"
    assert AdHocMaterialDialog._normalize_name("BLANK UNIVERSAL") == "blank universal"


def test_accept_persists_all_engineering_fields_and_reuses_normalized_duplicate(monkeypatch):
    _qapp()
    engine, factory = _session_factory()
    monkeypatch.setattr(dialog_module, "get_session_factory", lambda: factory)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.Ok))

    first = AdHocMaterialDialog()
    _fill(first, name="  Test   Material  ")
    first._accept()

    assert first.material() is not None
    first_id = first.material().id

    with factory() as session:
        stored = session.scalar(select(MaterialORM).where(MaterialORM.id == first_id))
        assert stored is not None
        assert stored.material_name == "Test Material"
        assert stored.manufacturer == "ООО Тест"
        assert stored.brand == "Test Brand"
        assert stored.material_type == MaterialType.PRIMER.value
        assert stored.binder_type == BinderType.EPOXY.value
        assert stored.density == 1.47
        assert stored.solids_by_volume_percent == 72.5
        assert stored.price_per_kg == 845.30
        assert stored.recommended_dft_min == 80
        assert stored.recommended_dft_max == 160
        assert stored.max_single_layer_dft == 200
        assert stored.is_two_component is True
        assert stored.is_active is True
        assert stored.is_incomplete is False

    second = AdHocMaterialDialog()
    _fill(second, name="TEST    MATERIAL")
    second._accept()

    assert second.material() is not None
    assert second.material().id == first_id

    with factory() as session:
        assert session.query(MaterialORM).count() == 1

    engine.dispose()
