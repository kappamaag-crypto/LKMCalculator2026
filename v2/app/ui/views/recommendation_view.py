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
    system_selected = Signal(object)

    def __init__(self, service: RecommendationService, parent=None):
        super().__init__(parent)
        self.service = service
        self._systems: list[CoatingSystem] = []
        self._last_result: RecommendationResult | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("\u041f\u043e\u0434\u0431\u043e\u0440 \u0441\u0438\u0441\u0442\u0435\u043c \u0410\u041a\u0417")
        title.setProperty("heading", True)
        root.addWidget(title)

        sub = QLabel("\u0423\u043a\u0430\u0436\u0438\u0442\u0435 \u0443\u0441\u043b\u043e\u0432\u0438\u044f \u044d\u043a\u0441\u043f\u043b\u0443\u0430\u0442\u0430\u0446\u0438\u0438 \u2014 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u043f\u043e\u0434\u0431\u0435\u0440\u0451\u0442 \u0438 \u0440\u0430\u043d\u0436\u0438\u0440\u0443\u0435\u0442 \u043f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0438\u0435 \u0441\u0438\u0441\u0442\u0435\u043c\u044b")
        sub.setProperty("subheading", True)
        root.addWidget(sub)

        splitter = QSplitter(Qt.Horizontal)

        left = QGroupBox("\u0423\u0441\u043b\u043e\u0432\u0438\u044f \u043e\u0431\u044a\u0435\u043a\u0442\u0430")
        form = QFormLayout(left)
        self.ed_object = QLineEdit()
        self.cmb_corrosion = QComboBox()
        self.cmb_corrosion.addItem("\u2014 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u043e \u2014", None)
        for c in CorrosionCategory:
            self.cmb_corrosion.addItem(c.value, c)
        self.cmb_durability = QComboBox()
        self.cmb_durability.addItem("\u2014 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u043e \u2014", None)
        for d in DurabilityLevel:
            self.cmb_durability.addItem(d.value, d)
        self.cmb_surface = QComboBox()
        self.cmb_surface.addItem("\u2014 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u043e \u2014", None)
        for s in SurfaceType:
            self.cmb_surface.addItem(s.value, s)
        self.cmb_environment = QComboBox()
        self.cmb_environment.addItem("\u2014 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u043e \u2014", None)
        for e in EnvironmentType:
            self.cmb_environment.addItem(e.value, e)
        self.spin_tmin = QDoubleSpinBox()
        self.spin_tmin.setRange(-100, 200)
        self.spin_tmin.setValue(-40)
        self.spin_tmin.setSuffix(" \u00b0C")
        self.spin_tmax = QDoubleSpinBox()
        self.spin_tmax.setRange(-100, 300)
        self.spin_tmax.setValue(60)
        self.spin_tmax.setSuffix(" \u00b0C")

        form.addRow("\u041e\u0431\u044a\u0435\u043a\u0442:", self.ed_object)
        form.addRow("\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f:", self.cmb_corrosion)
        form.addRow("\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c:", self.cmb_durability)
        form.addRow("\u041f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u044c:", self.cmb_surface)
        form.addRow("\u0421\u0440\u0435\u0434\u0430:", self.cmb_environment)
        form.addRow("T \u043c\u0438\u043d:", self.spin_tmin)
        form.addRow("T \u043c\u0430\u043a\u0441:", self.spin_tmax)

        btn_find = QPushButton("\u041f\u043e\u0434\u043e\u0431\u0440\u0430\u0442\u044c \u0441\u0438\u0441\u0442\u0435\u043c\u044b")
        btn_find.clicked.connect(self._on_recommend)
        form.addRow(btn_find)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_status = QLabel("\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u00ab\u041f\u043e\u0434\u043e\u0431\u0440\u0430\u0442\u044c \u0441\u0438\u0441\u0442\u0435\u043c\u044b\u00bb")
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
                self, "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445",
                "\u041a\u0430\u0442\u0430\u043b\u043e\u0433 \u0441\u0438\u0441\u0442\u0435\u043c \u043f\u0443\u0441\u0442.\n\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u0432\u043e \u0432\u043a\u043b\u0430\u0434\u043a\u0435 \u00ab\u0421\u0438\u0441\u0442\u0435\u043c\u044b\u00bb \u0438\u043b\u0438 \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 \u0434\u0435\u043c\u043e."
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
            self.list_results.addItem("\u041f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0438\u0445 \u0441\u0438\u0441\u0442\u0435\u043c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e")
            return
        for item in result.items:
            text = f"\u2605 {item.rank}.  {item.system.system_name}   \u2014   {item.score:.0f}/100"
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
            f"\u0421\u0438\u0441\u0442\u0435\u043c\u0430: {item.system.system_name}",
            f"\u041e\u0446\u0435\u043d\u043a\u0430: {item.score:.0f}/100  (\u043c\u0435\u0441\u0442\u043e {item.rank})",
            "",
            "\u041f\u0440\u0438\u0447\u0438\u043d\u044b \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438:",
        ]
        for r in item.reasons:
            lines.append(f"  \u2713 {r}")
        if item.warnings:
            lines.append("")
            lines.append("\u041f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f:")
            for w in item.warnings:
                lines.append(f"  \u26a0 {w}")
        if item.limitations:
            lines.append("")
            lines.append("\u041e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f:")
            for lim in item.limitations:
                lines.append(f"  \u2022 {lim}")
        self.txt_details.setPlainText("\n".join(lines))
        self.system_selected.emit(item.system)
