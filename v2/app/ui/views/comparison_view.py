"""Экран сравнения систем."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

from app.domain.models import ComparisonResult, ObjectData
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService


class ComparisonView(QWidget):
    def __init__(self, service: CalculationService, parent=None):
        super().__init__(parent)
        self.service = service
        self._systems_data: list[tuple[str, list[LayerInput]]] = []
        self._object = ObjectData(area_m2=100.0)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("\u0421\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435 \u0441\u0438\u0441\u0442\u0435\u043c")
        title.setProperty("heading", True)
        root.addWidget(title)

        sub = QLabel("\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 2\u201310 \u0441\u0438\u0441\u0442\u0435\u043c \u0434\u043b\u044f \u0441\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u044f. \u041c\u043e\u0436\u043d\u043e \u043f\u0435\u0440\u0435\u043d\u0435\u0441\u0442\u0438 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 \u0438\u0437 \u0432\u043a\u043b\u0430\u0434\u043a\u0438 \u00ab\u0420\u0430\u0441\u0447\u0451\u0442\u00bb.")
        sub.setProperty("subheading", True)
        root.addWidget(sub)

        btn_row = QHBoxLayout()
        self.btn_compare = QPushButton("\u0421\u0440\u0430\u0432\u043d\u0438\u0442\u044c")
        self.btn_compare.clicked.connect(self._on_compare)
        self.btn_clear = QPushButton("\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c")
        self.btn_clear.setProperty("secondary", True)
        self.btn_clear.clicked.connect(self._on_clear)
        self.lbl_count = QLabel("\u0421\u0438\u0441\u0442\u0435\u043c: 0")
        btn_row.addWidget(self.btn_compare)
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.lbl_count)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table)

        self.lbl_legend = QLabel()
        self.lbl_legend.setProperty("subheading", True)
        root.addWidget(self.lbl_legend)

    def set_object(self, obj: ObjectData) -> None:
        self._object = obj

    def add_system(self, name: str, layers: list[LayerInput]) -> None:
        if len(self._systems_data) >= 10:
            QMessageBox.warning(self, "\u041b\u0438\u043c\u0438\u0442", "\u041c\u0430\u043a\u0441\u0438\u043c\u0443\u043c 10 \u0441\u0438\u0441\u0442\u0435\u043c \u0434\u043b\u044f \u0441\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u044f")
            return
        self._systems_data.append((name, layers))
        self.lbl_count.setText(f"\u0421\u0438\u0441\u0442\u0435\u043c: {len(self._systems_data)}")

    def add_from_calculation(self, result) -> None:
        name = result.system.system_name or f"\u0421\u0438\u0441\u0442\u0435\u043c\u0430 {len(self._systems_data)+1}"
        layers = [
            LayerInput(
                material=lr.material,
                target_dft=lr.target_dft,
                losses_percent=lr.losses_percent,
                thinner_percent=lr.thinner_percent,
                thinner=lr.thinner,
            )
            for lr in result.layers
        ]
        self.add_system(name, layers)
        if result.object_data.area_m2 > 0:
            self._object = result.object_data

    def _on_clear(self) -> None:
        self._systems_data.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c"])
        self.lbl_count.setText("\u0421\u0438\u0441\u0442\u0435\u043c: 0")
        self.lbl_legend.clear()

    def _on_compare(self) -> None:
        if len(self._systems_data) < 2:
            QMessageBox.warning(self, "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435", "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u043d\u0435 \u043c\u0435\u043d\u0435\u0435 2 \u0441\u0438\u0441\u0442\u0435\u043c")
            return
        comparison = self.service.compare_systems(self._object, self._systems_data)
        self._fill_table(comparison)

    def _fill_table(self, comparison: ComparisonResult) -> None:
        systems = comparison.systems
        n = len(systems)
        self.table.setColumnCount(n + 1)
        headers = ["\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c"] + [
            (s.system.system_name or f"\u0421\u0438\u0441\u0442\u0435\u043c\u0430 {i+1}")[:30] for i, s in enumerate(systems)
        ]
        self.table.setHorizontalHeaderLabels(headers)

        rows_data = [
            ("\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u0441\u043b\u043e\u0451\u0432", [len(s.layers) for s in systems]),
            ("\u041e\u0431\u0449\u0430\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430, \u043c\u043a\u043c", [s.total_dft for s in systems]),
            ("\u0420\u0430\u0441\u0445\u043e\u0434, \u043a\u0433/\u043c\u00b2", [s.total_practical_consumption_kg for s in systems]),
            ("\u0420\u0430\u0441\u0445\u043e\u0434, \u043b/\u043c\u00b2", [s.total_practical_consumption_l for s in systems]),
            ("\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c, \u0440\u0443\u0431/\u043c\u00b2", [s.total_cost_per_m2 for s in systems]),
            ("\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u043e\u0431\u044a\u0435\u043a\u0442\u0430, \u0440\u0443\u0431", [s.total_cost for s in systems]),
        ]

        self.table.setRowCount(len(rows_data))
        green = QBrush(QColor("#d1fae5"))
        red = QBrush(QColor("#fee2e2"))

        for r, (label, values) in enumerate(rows_data):
            self.table.setItem(r, 0, QTableWidgetItem(label))
            min_v = min(values) if values else 0
            max_v = max(values) if values else 0
            for c, v in enumerate(values):
                if isinstance(v, float):
                    text = f"{v:.2f}" if abs(v) < 1000 else f"{v:,.0f}".replace(",", " ")
                else:
                    text = str(v)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if label.startswith("\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c") or label.startswith("\u0420\u0430\u0441\u0445\u043e\u0434") or label.startswith("\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e"):
                    if v == min_v:
                        item.setBackground(green)
                    elif v == max_v and min_v != max_v:
                        item.setBackground(red)
                elif label.startswith("\u041e\u0431\u0449\u0430\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430"):
                    if v == max_v:
                        item.setBackground(green)
                self.table.setItem(r, c + 1, item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        legend_parts = []
        if comparison.cheapest_index is not None:
            legend_parts.append(f"\u0421\u0430\u043c\u0430\u044f \u0434\u0435\u0448\u0451\u0432\u0430\u044f: {headers[comparison.cheapest_index+1]}")
        if comparison.best_balance_index is not None:
            legend_parts.append(f"\u041b\u0443\u0447\u0448\u0438\u0439 \u0431\u0430\u043b\u0430\u043d\u0441: {headers[comparison.best_balance_index+1]}")
        self.lbl_legend.setText("  |  ".join(legend_parts))
