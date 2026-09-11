"""Headless smoke test for the §24 chemical-resistance UI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.models import Material
from app.services.calculation_service import CalculationService
from app.ui.dialogs.chemical_resistance_dialog import ChemicalResistanceDialog


def test_chemical_resistance_dialog_preserves_unknown_without_rules():
    app = QApplication.instance() or QApplication([])
    material = Material(material_name="Generic Epoxy")
    dialog = ChemicalResistanceDialog(CalculationService(), [material])
    dialog.agent_id.setText("H2SO4")
    dialog.agent_name.setText("Серная кислота")
    dialog.refresh()
    assert "UNKNOWN" in dialog.status_label.text()
    assert "CHEM_RESISTANCE_UNKNOWN" in dialog.report.toPlainText()
    dialog.close()
    app.processEvents()
