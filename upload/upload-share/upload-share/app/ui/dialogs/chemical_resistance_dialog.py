"""UI for explicit source-backed chemical resistance checks."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from app.domain.chemical_resistance import ChemicalAgent
from app.domain.models import Material
from app.services.calculation_service import CalculationService


class ChemicalResistanceDialog(QDialog):
    """Run and display a chemical-resistance check without inventing rules."""

    def __init__(self, service: CalculationService, materials: list[Material], parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.materials = materials
        self.setWindowTitle("Проверка химстойкости")
        self.resize(820, 560)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.material_combo = QComboBox()
        for material in materials:
            self.material_combo.addItem(material.display_name(), material.material_name or material.display_name())
        form.addRow("Материал:", self.material_combo)
        self.agent_id = QLineEdit()
        self.agent_id.setPlaceholderText("например: H2SO4")
        form.addRow("Среда / agent ID:", self.agent_id)
        self.agent_name = QLineEdit()
        form.addRow("Наименование среды:", self.agent_name)
        self.concentration = self._number(0.0, 100.0, 2)
        form.addRow("Концентрация, %:", self.concentration)
        self.temperature = self._number(-100.0, 500.0, 1)
        form.addRow("Температура, °C:", self.temperature)
        root.addLayout(form)

        controls = QHBoxLayout()
        self.check_button = QPushButton("Проверить")
        self.check_button.clicked.connect(self.refresh)
        controls.addWidget(self.check_button)
        root.addLayout(controls)

        self.status_label = QLabel("Статус: —")
        root.addWidget(self.status_label)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        root.addWidget(self.report)

    @staticmethod
    def _number(minimum: float, maximum: float, decimals: int) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSpecialValueText("не задано")
        spin.setValue(minimum if minimum < 0 else 0.0)
        return spin

    def refresh(self) -> None:
        material = self.material_combo.currentData()
        agent = self.agent_id.text().strip()
        if not material:
            self.status_label.setText("Статус: нет материала")
            return
        if not agent:
            self.status_label.setText("Статус: укажите agent ID")
            return
        check = self.service.check_chemical_resistance(
            [material],
            [ChemicalAgent(
                agent_id=agent,
                name=self.agent_name.text().strip(),
                concentration_percent=self.concentration.value(),
                temperature_c=self.temperature.value(),
            )],
            require_known=False,
        )
        outcome = check.outcomes.get(material, {}).get(agent, "UNKNOWN")
        self.status_label.setText(f"Результат: <b>{outcome}</b>")
        self.report.setPlainText("\n".join(check.summary_lines()))
