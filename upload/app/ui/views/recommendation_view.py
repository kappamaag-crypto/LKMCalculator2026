"""Экран подбора систем АКЗ."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QMessageBox, QSplitter,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.domain.models import ObjectData, CoatingSystem, RecommendationResult
from app.domain.enums import CorrosionCategory, DurabilityLevel, SurfaceType, EnvironmentType
from app.services.recommendation_service import RecommendationService


class RecommendationView(QWidget):
    """Вкладка «Рекомендации»."""

    system_selected = Signal(object)  # CoatingSystem

    def __init__(self, service: RecommendationService, parent=None):
        super().__init__(parent)
        self.service = service
        self._systems: list[CoatingSystem] = []
        self._last_result: RecommendationResult | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Подбор систем АКЗ")
        title.setProperty("heading", True)
        root.addWidget(title)

        sub = QLabel("Укажите условия эксплуатации — программа подберёт и ранжирует подходящие системы")
        sub.setProperty("subheading", True)
        root.addWidget(sub)

        splitter = QSplitter(Qt.Horizontal)

        # --- Условия ---
        left = QGroupBox("Условия объекта")
        form = QFormLayout(left)
        self.ed_object = QLineEdit()
        self.cmb_corrosion = QComboBox()
        self.cmb_corrosion.addItem("— не задано —", None)
        for c in CorrosionCategory:
            self.cmb_corrosion.addItem(c.value, c)
        self.cmb_durability = QComboBox()
        self.cmb_durability.addItem("— не задано —", None)
        for d in DurabilityLevel:
            self.cmb_durability.addItem(d.value, d)
        self.cmb_surface = QComboBox()
        self.cmb_surface.addItem("— не задано —", None)
        for s in SurfaceType:
            self.cmb_surface.addItem(s.value, s)
        self.cmb_environment = QComboBox()
        self.cmb_environment.addItem("— не задано —", None)
        for e in EnvironmentType:
            self.cmb_environment.addItem(e.value, e)
        self.spin_tmin = QDoubleSpinBox()
        self.spin_tmin.setRange(-100, 200)
        self.spin_tmin.setValue(-40)
        self.spin_tmin.setSuffix(" °C")
        self.spin_tmax = QDoubleSpinBox()
        self.spin_tmax.setRange(-100, 300)
        self.spin_tmax.setValue(60)
        self.spin_tmax.setSuffix(" °C")

        form.addRow("Объект:", self.ed_object)
        form.addRow("Категория:", self.cmb_corrosion)
        form.addRow("Долговечность:", self.cmb_durability)
        form.addRow("Поверхность:", self.cmb_surface)
        form.addRow("Среда:", self.cmb_environment)
        form.addRow("T мин:", self.spin_tmin)
        form.addRow("T макс:", self.spin_tmax)

        btn_find = QPushButton("Подобрать системы")
        btn_find.clicked.connect(self._on_recommend)
        form.addRow(btn_find)

        splitter.addWidget(left)

        # --- Результаты ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_status = QLabel("Нажмите «Подобрать системы»")
        self.lbl_status.setProperty("subheading", True)
        right_layout.addWidget(self.lbl_status)

        self.list_results = QListWidget()
        self.list_results.currentRowChanged.connect(self._on_select)
        right_layout.addWidget(self.list_results)

        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setMaximumHeight(200)
        right_layout.addWidget(self.txt_details)

        self.lbl_disclaimer = QLabel()
        self.lbl_disclaimer.setWordWrap(True)
        self.lbl_disclaimer.setProperty("subheading", True)
        self.lbl_disclaimer.setStyleSheet("color: #92400e; background: #fef3c7; padding: 8px; border-radius: 4px;")
        right_layout.addWidget(self.lbl_disclaimer)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter)

    def set_systems(self, systems: list[CoatingSystem]) -> None:
        self._systems = list(systems)

    def _on_recommend(self) -> None:
        if not self._systems:
            QMessageBox.information(
                self, "Нет данных",
                "Каталог систем пуст.\nДобавьте системы во вкладке «Системы» или загрузите демо."
            )
            return

        obj = ObjectData(
            object_name=self.ed_object.text().strip(),
            corrosion_category=self.cmb_corrosion.currentData(),
            durability=self.cmb_durability.currentData(),
            surface_type=self.cmb_surface.currentData(),
            environment=self.cmb_environment.currentData(),
            temperature_min=self.spin_tmin.value(),
            temperature_max=self.spin_tmax.value(),
        )
        result = self.service.recommend(obj, self._systems, top_n=10, calculate_costs=False)
        self._last_result = result
        self._show_result(result)

    def _show_result(self, result: RecommendationResult) -> None:
        self.list_results.clear()
        self.txt_details.clear()
        self.lbl_status.setText(result.message)
        self.lbl_disclaimer.setText(result.disclaimer)

        if not result.items:
            self.list_results.addItem("Подходящих систем не найдено")
            return

        for item in result.items:
            text = f"★ {item.rank}.  {item.system.system_name}   —   {item.score:.0f}/100"
            lw = QListWidgetItem(text)
            lw.setData(Qt.UserRole, item)
            font = QFont()
            if item.rank == 1:
                font.setBold(True)
            lw.setFont(font)
            self.list_results.addItem(lw)

        if self.list_results.count() > 0:
            self.list_results.setCurrentRow(0)

    def _on_select(self, row: int) -> None:
        if row < 0 or not self._last_result or row >= len(self._last_result.items):
            return
        item = self._last_result.items[row]
        lines = [
            f"Система: {item.system.system_name}",
            f"Оценка: {item.score:.0f}/100  (место {item.rank})",
            "",
            "Причины рекомендации:",
        ]
        for r in item.reasons:
            lines.append(f"  ✓ {r}")
        if item.warnings:
            lines.append("")
            lines.append("Предупреждения:")
            for w in item.warnings:
                lines.append(f"  ⚠ {w}")
        if item.limitations:
            lines.append("")
            lines.append("Ограничения:")
            for lim in item.limitations:
                lines.append(f"  • {lim}")
        self.txt_details.setPlainText("\n".join(lines))
        self.system_selected.emit(item.system)