"""Таблица слоёв для инженерного расчёта."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt, Signal

from app.domain.models import LayerResult
from app.domain.calculator import LayerInput

COLUMNS = [
    ("№", 40), ("Материал", 220), ("Связующее", 100), ("2К", 45),
    ("DFT, мкм", 80), ("Потери, %", 75), ("Разб., %", 70),
    ("WFT, мкм", 80), ("Расход, кг/м²", 100), ("Стоимость, руб/м²", 120),
]


class LayerTableWidget(QTableWidget):
    """Редактируемая таблица слоёв без закупочных/складских показателей."""

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

    @staticmethod
    def _item(text: str, align=Qt.AlignCenter) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def set_layers(self, layers: list[LayerInput], results: list[LayerResult] | None = None) -> None:
        self._layer_inputs = list(layers)
        self.setRowCount(len(layers))
        for row, layer in enumerate(layers):
            self._fill_row(row, layer, results[row] if results and row < len(results) else None)

    def _fill_row(self, row: int, li: LayerInput, result: LayerResult | None) -> None:
        self.setItem(row, 0, self._item(str(row + 1)))
        self.setItem(row, 1, self._item(li.material.material_name, Qt.AlignLeft | Qt.AlignVCenter))
        binder = li.material.binder_type.value if hasattr(li.material.binder_type, "value") else str(li.material.binder_type)
        self.setItem(row, 2, self._item(binder))
        self.setItem(row, 3, self._item("Да" if li.material.is_two_component else "Нет"))
        self.setItem(row, 4, self._item(f"{li.target_dft:.0f}"))
        self.setItem(row, 5, self._item(f"{li.losses_percent:.0f}"))
        self.setItem(row, 6, self._item(f"{li.thinner_percent:.0f}"))
        if result:
            values = (f"{result.wft:.1f}", f"{result.practical_consumption_kg:.3f}", f"{result.cost_per_m2 + result.thinner_cost_per_m2:.2f}")
        else:
            values = ("—", "—", "—")
        for col, value in zip((7, 8, 9), values):
            self.setItem(row, col, self._item(value))

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
        for r in range(self.rowCount()):
            self.item(r, 0).setText(str(r + 1))
        self.layer_changed.emit()

    def clear_layers(self) -> None:
        self._layer_inputs.clear()
        self.setRowCount(0)
        self.layer_changed.emit()
