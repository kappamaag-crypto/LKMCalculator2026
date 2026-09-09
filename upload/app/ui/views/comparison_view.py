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
    """Вкладка «Сравнение»."""

    def __init__(self, service: CalculationService, parent=None):
        super().__init__(parent)
        self.service = service
        self._systems_data: list[tuple[str, list[LayerInput]]] = []
        self._object = ObjectData(area_m2=1.0)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Сравнение систем")
        title.setProperty("heading", True)
        root.addWidget(title)

        sub = QLabel(
            "Добавьте 2–10 систем для сравнения. Площадь берётся из текущего расчёта."
        )
        sub.setProperty("subheading", True)
        root.addWidget(sub)

        btn_row = QHBoxLayout()
        self.btn_compare = QPushButton("Сравнить")
        self.btn_compare.clicked.connect(self._on_compare)
        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.setProperty("secondary", True)
        self.btn_clear.clicked.connect(self._on_clear)
        self.lbl_count = QLabel("Систем: 0")
        btn_row.addWidget(self.btn_compare)
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.lbl_count)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Показатель"])
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
            QMessageBox.warning(self, "Лимит", "Максимум 10 систем для сравнения")
            return
        self._systems_data.append((name, layers))
        self.lbl_count.setText(f"Систем: {len(self._systems_data)}")

    def add_from_calculation(self, result) -> None:
        """Добавить результат расчёта в сравнение."""
        name = result.system.system_name or f"Система {len(self._systems_data)+1}"
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
        area = result.object_data.area_m2
        if area is not None and area > 0:
            self._object = result.object_data

    def _on_clear(self) -> None:
        self._systems_data.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["Показатель"])
        self.lbl_count.setText("Систем: 0")
        self.lbl_legend.clear()

    def _on_compare(self) -> None:
        if len(self._systems_data) < 2:
            QMessageBox.warning(self, "Внимание", "Добавьте не менее 2 систем")
            return

        try:
            comparison = self.service.compare_systems(self._object, self._systems_data)
        except ValueError as exc:
            QMessageBox.warning(self, "Расчёт невозможен", str(exc))
            return
        self._fill_table(comparison)

    @staticmethod
    def _format_value(value) -> str:
        if value is None:
            return "—"
        if isinstance(value, float):
            if abs(value) < 1000:
                return f"{value:.2f}"
            return f"{value:,.0f}".replace(",", " ")
        return str(value)

    def _fill_table(self, comparison: ComparisonResult) -> None:
        systems = comparison.systems
        n = len(systems)
        self.table.setColumnCount(n + 1)
        headers = ["Показатель"] + [
            (s.system.system_name or f"Система {i+1}")[:30]
            for i, s in enumerate(systems)
        ]
        self.table.setHorizontalHeaderLabels(headers)

        rows_data = [
            ("Количество слоёв", [len(s.layers) for s in systems], False),
            ("Общая толщина, мкм", [s.total_dft for s in systems], False),
            ("Расход ЛКМ, кг/м²", [s.total_practical_consumption_kg for s in systems], True),
            ("Расход ЛКМ, л/м²", [s.total_practical_consumption_l for s in systems], True),
            ("Стоимость, руб/м²", [s.total_cost_per_m2 for s in systems], True),
            ("Стоимость объекта, руб", [s.total_cost for s in systems], True),
        ]

        self.table.setRowCount(len(rows_data))
        green = QBrush(QColor("#d1fae5"))
        red = QBrush(QColor("#fee2e2"))

        for r, (label, values, highlight_min) in enumerate(rows_data):
            self.table.setItem(r, 0, QTableWidgetItem(label))
            numeric = [
                v for v in values
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            min_v = min(numeric) if numeric else None
            max_v = max(numeric) if numeric else None

            for c, v in enumerate(values):
                item = QTableWidgetItem(self._format_value(v))
                item.setTextAlignment(Qt.AlignCenter)
                if highlight_min and numeric and isinstance(v, (int, float)):
                    if v == min_v:
                        item.setBackground(green)
                    elif v == max_v and min_v != max_v:
                        item.setBackground(red)
                self.table.setItem(r, c + 1, item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        legend_parts = []
        if comparison.cheapest_index is not None:
            legend_parts.append(f"Самая дешёвая: {headers[comparison.cheapest_index + 1]}")
        if comparison.best_balance_index is not None:
            legend_parts.append(f"Лучший баланс: {headers[comparison.best_balance_index + 1]}")
        self.lbl_legend.setText("  |  ".join(legend_parts))
