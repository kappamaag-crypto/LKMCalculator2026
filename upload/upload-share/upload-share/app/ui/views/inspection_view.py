"""Inspection workflow UI."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QLineEdit, QPlainTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox, QDoubleSpinBox, QWidget,
)
from app.domain.inspection import DftMeasurementPoint
from app.services.inspection_service import InspectionService


class InspectionView(QWidget):
    record_created = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = InspectionService()
        self._calculation_result = None
        self._points: list[DftMeasurementPoint] = []

        form_box = QGroupBox("Инспекция / контроль качества")
        form = QFormLayout(form_box)
        self.inspection_id = QLineEdit()
        self.object_name = QLineEdit()
        self.inspector = QLineEdit()
        self.standard = QLineEdit()
        self.source = QLineEdit()
        self.system = QLineEdit()
        self.status = QLineEdit("UNKNOWN")
        for label, widget in (("№", self.inspection_id), ("Объект", self.object_name), ("Инспектор", self.inspector), ("НД", self.standard), ("Источник", self.source), ("Система", self.system), ("Статус", self.status)):
            form.addRow(label, widget)

        dft_box = QGroupBox("DFT — контроль толщины сухой плёнки")
        dft_form = QFormLayout(dft_box)
        self.dft_layer = QSpinBox(); self.dft_layer.setRange(1, 999); self.dft_layer.setValue(1)
        self.dft_point = QLineEdit(); self.dft_point.setPlaceholderText("P1")
        self.dft_value = QDoubleSpinBox(); self.dft_value.setRange(0, 100000); self.dft_value.setDecimals(2); self.dft_value.setSuffix(" мкм")
        self.dft_instrument = QLineEdit()
        self.dft_notes = QLineEdit()
        dft_form.addRow("Слой №", self.dft_layer); dft_form.addRow("Точка", self.dft_point)
        dft_form.addRow("DFT", self.dft_value); dft_form.addRow("Прибор", self.dft_instrument); dft_form.addRow("Примечание", self.dft_notes)
        dft_buttons = QHBoxLayout()
        self.add_dft = QPushButton("Добавить измерение")
        self.add_dft.clicked.connect(self._add_dft)
        self.evaluate_dft = QPushButton("Проверить DFT")
        self.evaluate_dft.clicked.connect(self._evaluate_dft)
        dft_buttons.addWidget(self.add_dft); dft_buttons.addWidget(self.evaluate_dft); dft_buttons.addStretch()
        dft_form.addRow(dft_buttons)

        self.notes = QPlainTextEdit()
        self.create = QPushButton("Создать запись")
        self.create.clicked.connect(self._create)
        self.summary = QPlainTextEdit(); self.summary.setReadOnly(True)
        root = QVBoxLayout(self)
        root.addWidget(form_box); root.addWidget(dft_box); root.addWidget(self.notes); root.addWidget(self.create); root.addWidget(self.summary)

    def set_calculation_result(self, result) -> None:
        """Provide the latest calculation as the source for DFT layer limits."""
        self._calculation_result = result

    def _add_dft(self):
        point_id = self.dft_point.text().strip()
        if not point_id:
            self.summary.setPlainText("Укажите идентификатор точки DFT.")
            return
        try:
            point = DftMeasurementPoint(
                layer_index=self.dft_layer.value() - 1,
                point_id=point_id,
                measured_dft_um=self.dft_value.value(),
                instrument=self.dft_instrument.text().strip(),
                notes=self.dft_notes.text().strip(),
            )
        except ValueError as exc:
            self.summary.setPlainText(str(exc)); return
        self._points.append(point)
        self.summary.setPlainText(f"Добавлено измерение: L{point.layer_index + 1} {point.point_id} = {point.measured_dft_um:g} мкм. Всего точек: {len(self._points)}")

    def _evaluate_dft(self):
        if not self._points:
            self.summary.setPlainText("Добавьте хотя бы одно DFT-измерение."); return
        if self._calculation_result is None:
            self.summary.setPlainText("Нет результата расчёта. Сначала выполните расчёт в разделе «Расчёт»."); return
        report = self.service.evaluate_dft_against_calculation(self._points, self._calculation_result)
        self.summary.setPlainText(self.service.format_dft_report(report))

    def _create(self):
        record = self.service.create_record_with_dft_from_calculation(
            self.inspection_id.text(), self._points, self._calculation_result,
            object_name=self.object_name.text(), inspector=self.inspector.text(),
            standard_reference=self.standard.text(), standard_source=self.source.text(),
            coating_system=self.system.text(), notes=self.notes.toPlainText(),
            acceptance_status=self.status.text().strip() or "UNKNOWN",
        ) if self._points and self._calculation_result is not None else self.service.create_record(
            self.inspection_id.text(), object_name=self.object_name.text(), inspector=self.inspector.text(),
            standard_reference=self.standard.text(), standard_source=self.source.text(),
            coating_system=self.system.text(), notes=self.notes.toPlainText(),
            acceptance_status=self.status.text().strip() or "UNKNOWN",
        )
        self.summary.setPlainText(self.service.summary(record))
        self.record_created.emit(record)
