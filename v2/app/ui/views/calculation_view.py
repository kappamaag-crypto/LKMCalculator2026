"""Э\u043a\u0440\u0430\u043d \u0440\u0430\u0441\u0447\u0451\u0442\u0430 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u044f."""

from __future__ import annotations

from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QPushButton, QMessageBox, QTextEdit, QSplitter, QFileDialog,
)
from PySide6.QtCore import Qt, Signal

from app.domain.models import Material, ObjectData
from app.domain.enums import (
    CorrosionCategory, DurabilityLevel, SurfaceType, EnvironmentType,
)
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService
from app.ui.widgets.layer_table import LayerTableWidget
from app.infrastructure.export.excel_exporter import ExcelExporter
from app.infrastructure.export.pdf_exporter import PDFExporter


class CalculationView(QWidget):
    calculation_done = Signal(object)

    def __init__(self, service: CalculationService, parent=None):
        super().__init__(parent)
        self.service = service
        self._materials: list[Material] = []
        self._last_result = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("\u0420\u0430\u0441\u0447\u0451\u0442 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u044f")
        title.setProperty("heading", True)
        root.addWidget(title)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        obj_box = QGroupBox("\u041e\u0431\u044a\u0435\u043a\u0442")
        obj_form = QFormLayout(obj_box)
        self.ed_object = QLineEdit()
        self.ed_customer = QLineEdit()
        self.spin_area = QDoubleSpinBox()
        self.spin_area.setRange(0, 1_000_000)
        self.spin_area.setValue(100.0)
        self.spin_area.setSuffix(" \u043c\u00b2")
        self.spin_area.setDecimals(2)
        obj_form.addRow("\u041e\u0431\u044a\u0435\u043a\u0442:", self.ed_object)
        obj_form.addRow("\u0417\u0430\u043a\u0430\u0437\u0447\u0438\u043a:", self.ed_customer)
        obj_form.addRow("\u041f\u043b\u043e\u0449\u0430\u0434\u044c:", self.spin_area)
        left_layout.addWidget(obj_box)

        cond_box = QGroupBox("\u0423\u0441\u043b\u043e\u0432\u0438\u044f")
        cond_form = QFormLayout(cond_box)
        self.cmb_corrosion = QComboBox()
        self.cmb_corrosion.addItem("\u2014 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u043e \u2014", None)
        for c in CorrosionCategory:
            self.cmb_corrosion.addItem(c.value, c)
        self.cmb_durability = QComboBox()
        self.cmb_durability.addItem("\u2014 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u043e \u2014", None)
        for d in DurabilityLevel:
            self.cmb_durability.addItem(d.value, d)
        cond_form.addRow("\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f:", self.cmb_corrosion)
        cond_form.addRow("\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c:", self.cmb_durability)
        left_layout.addWidget(cond_box)

        layer_box = QGroupBox("\u0421\u043b\u043e\u0438")
        layer_layout = QVBoxLayout(layer_box)
        mat_row = QHBoxLayout()
        self.cmb_material = QComboBox()
        self.spin_dft = QDoubleSpinBox()
        self.spin_dft.setRange(1, 2000)
        self.spin_dft.setValue(100)
        self.spin_dft.setSuffix(" \u043c\u043a\u043c")
        self.spin_losses = QDoubleSpinBox()
        self.spin_losses.setRange(0, 99)
        self.spin_losses.setValue(0)
        self.spin_losses.setSuffix(" %")
        mat_row.addWidget(self.cmb_material, 2)
        mat_row.addWidget(self.spin_dft)
        mat_row.addWidget(self.spin_losses)
        layer_layout.addLayout(mat_row)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u043b\u043e\u0439")
        btn_add.clicked.connect(self._on_add_layer)
        btn_del = QPushButton("\u0423\u0434\u0430\u043b\u0438\u0442\u044c")
        btn_del.setProperty("secondary", True)
        btn_del.clicked.connect(self._on_remove_layer)
        btn_clear = QPushButton("\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c")
        btn_clear.setProperty("secondary", True)
        btn_clear.clicked.connect(self._on_clear_layers)
        btn_demo = QPushButton("\u0414\u0435\u043c\u043e")
        btn_demo.setProperty("secondary", True)
        btn_demo.clicked.connect(self._on_load_demo)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addWidget(btn_clear)
        btn_row.addWidget(btn_demo)
        layer_layout.addLayout(btn_row)

        self.layer_table = LayerTableWidget()
        layer_layout.addWidget(self.layer_table)
        left_layout.addWidget(layer_box)

        calc_row = QHBoxLayout()
        btn_calc = QPushButton("\u0420\u0430\u0441\u0441\u0447\u0438\u0442\u0430\u0442\u044c")
        btn_calc.clicked.connect(self._on_calculate)
        btn_excel = QPushButton("Excel")
        btn_excel.setProperty("secondary", True)
        btn_excel.clicked.connect(self._on_excel)
        btn_pdf = QPushButton("PDF")
        btn_pdf.setProperty("secondary", True)
        btn_pdf.clicked.connect(self._on_pdf)
        calc_row.addWidget(btn_calc)
        calc_row.addWidget(btn_excel)
        calc_row.addWidget(btn_pdf)
        left_layout.addLayout(calc_row)
        left_layout.addStretch()

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442"))
        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        right_layout.addWidget(self.txt_result)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter)

    def set_materials(self, materials: list[Material]) -> None:
        self._materials = list(materials)
        self.cmb_material.clear()
        for m in self._materials:
            self.cmb_material.addItem(m.material_name, m)

    def _current_material(self) -> Optional[Material]:
        return self.cmb_material.currentData()

    def _build_object_data(self) -> ObjectData:
        return ObjectData(
            object_name=self.ed_object.text().strip(),
            customer=self.ed_customer.text().strip(),
            area_m2=self.spin_area.value(),
            corrosion_category=self.cmb_corrosion.currentData(),
            durability=self.cmb_durability.currentData(),
        )

    def _on_add_layer(self) -> None:
        mat = self._current_material()
        if mat is None:
            QMessageBox.warning(self, "\u0421\u043b\u043e\u0439", "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b")
            return
        li = LayerInput(material=mat, target_dft=self.spin_dft.value(), losses_percent=self.spin_losses.value())
        self.layer_table.add_layer(li)

    def _on_remove_layer(self) -> None:
        self.layer_table.remove_selected()

    def _on_clear_layers(self) -> None:
        self.layer_table.clear_layers()

    def _on_load_demo(self) -> None:
        if len(self._materials) < 2:
            return
        self.layer_table.clear_layers()
        self.layer_table.add_layer(LayerInput(material=self._materials[0], target_dft=200))
        self.layer_table.add_layer(LayerInput(material=self._materials[1], target_dft=100))
        self.ed_object.setText("\u0414\u0435\u043c\u043e-\u043e\u0431\u044a\u0435\u043a\u0442")
        self.spin_area.setValue(100)

    def _on_calculate(self) -> None:
        layers = self.layer_table.get_layer_inputs()
        if not layers:
            QMessageBox.warning(self, "\u0420\u0430\u0441\u0447\u0451\u0442", "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u0445\u043e\u0442\u044f \u0431\u044b \u043e\u0434\u0438\u043d \u0441\u043b\u043e\u0439")
            return
        obj = self._build_object_data()
        result, validation = self.service.calculate_system(obj, layers)
        if validation.has_errors:
            msgs = "\n".join(i.message for i in validation.errors)
            QMessageBox.critical(self, "\u041e\u0448\u0438\u0431\u043a\u0438 \u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u0438", msgs)
            return
        self._last_result = result
        self.layer_table.set_layers(layers, result.layers)
        summary = self.service.format_summary(result)
        if validation.has_warnings:
            summary += "\n\n\u041f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f:\n" + "\n".join(f"\u26a0 {i.message}" for i in validation.warnings)
        self.txt_result.setPlainText(summary)
        self.calculation_done.emit(result)

    def _on_excel(self) -> None:
        if not self._last_result:
            QMessageBox.information(self, "Excel", "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u0435 \u0440\u0430\u0441\u0447\u0451\u0442")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Excel", "calculation.xlsx", "Excel (*.xlsx)")
        if path:
            ExcelExporter().export_calculation(self._last_result, path)
            QMessageBox.information(self, "Excel", f"\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e:\n{path}")

    def _on_pdf(self) -> None:
        if not self._last_result:
            QMessageBox.information(self, "PDF", "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u0435 \u0440\u0430\u0441\u0447\u0451\u0442")
            return
        path, _ = QFileDialog.getSaveFileName(self, "PDF", "calculation.pdf", "PDF (*.pdf)")
        if path:
            PDFExporter().export_calculation(self._last_result, path)
            QMessageBox.information(self, "PDF", f"\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e:\n{path}")
