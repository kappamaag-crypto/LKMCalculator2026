"""Таблица слоёв для расчёта."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.domain.models import LayerResult
from app.domain.calculator import LayerInput
from app.domain.models import Material


COLUMNS = [
    ("№", 40),
    ("Материал", 220),
    ("Связующее", 100),
    ("DFT, мкм", 80),
    ("Потери, %", 75),
    ("Разб., %", 70),
    ("WFT, мкм", 80),
    ("Расход, кг/м²", 100),
    ("Стоимость, руб/м²", 120),
]


class LayerTableWidget(QTableWidget):
    """Редактируемая таблица слоёв."""

    layer_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i, (_, width) in enumerate(COLUMNS):
            if i != 1:
                self.setColumnWidth(i, width)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self._layer_inputs: list[LayerInput] = []

    def set_layers(self, layers: list[LayerInput], results: list[LayerResult] | None = None) -> None:
        self._layer_inputs = list(layers)
        self.setRowCount(len(layers))
        for row, li in enumerate(layers):
            result = results[row] if results and row < len(results) else None
            self._fill_row(row, li, result)

    def _fill_row(self, row: int, li: LayerInput, result: LayerResult | None) -> None:
        def item(text: str, editable: bool = False, align=Qt.AlignCenter):
            it = QTableWidgetItem(text)
            it.setTextAlignment(align)
            if not editable:
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            return it

        self.setItem(row, 0, item(str(row + 1)))
        self.setItem(row, 1, item(li.material.material_name, align=Qt.AlignLeft | Qt.AlignVCenter))
        binder = li.material.binder_type.value if hasattr(li.material.binder_type, "value") else str(li.material.binder_type)
        self.setItem(row, 2, item(binder))
        self.setItem(row, 3, item(f"{li.target_dft:.0f}"))
        self.setItem(row, 4, item(f"{li.losses_percent:.0f}"))
        self.setItem(row, 5, item(f"{li.thinner_percent:.0f}"))

        if result:
            self.setItem(row, 6, item(f"{result.wft:.1f}"))
            self.setItem(row, 7, item(f"{result.practical_consumption_kg:.3f}"))
            self.setItem(row, 8, item(f"{result.cost_per_m2:.2f}"))
        else:
            for col in (6, 7, 8):
                self.setItem(row, col, item("—"))

    def get_layer_inputs(self) -> list[LayerInput]:
        return list(self._layer_inputs)

    def add_layer(self, li: LayerInput) -> None:
        self._layer_inputs.append(li)
        row = self.rowCount()
        self.insertRow(row)
        self._fill_row(row, li, None)
        self.layer_changed.emit()

    def remove_selected(self) -> None:
        row = self.currentRow()
        if row < 0 or row >= len(self._layer_inputs):
            return
        self._layer_inputs.pop(row)
        self.removeRow(row)
        # Перенумеровать
        for r in range(self.rowCount()):
            self.item(r, 0).setText(str(r + 1))
        self.layer_changed.emit()

    def clear_layers(self) -> None:
        self._layer_inputs.clear()
        self.setRowCount(0)
        self.layer_changed.emit()