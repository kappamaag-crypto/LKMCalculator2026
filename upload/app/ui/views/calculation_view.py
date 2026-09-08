"""Экран быстрого / инженерного расчёта."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QPushButton, QMessageBox, QTextEdit, QSplitter, QFrame,
)
from PySide6.QtCore import Qt, Signal

from app.domain.models import Material, ObjectData
from app.domain.enums import (
    CorrosionCategory, DurabilityLevel, SurfaceType,
    EnvironmentType, MaterialType, BinderType,
)
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService
from app.ui.widgets.layer_table import LayerTableWidget
from app.infrastructure.export.excel_exporter import ExcelExporter
from app.infrastructure.export.pdf_exporter import PDFExporter
from pathlib import Path
from PySide6.QtWidgets import QFileDialog


class CalculationView(QWidget):
    """Вкладка «Расчёт»."""

    calculation_done = Signal(object)  # SystemCalculationResult

    def __init__(self, service: CalculationService, parent=None):
        super().__init__(parent)
        self.service = service
        self._materials: list[Material] = []
        self._last_result = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # --- Заголовок ---
        title = QLabel("Расчёт системы покрытия")
        title.setProperty("heading", True)
        root.addWidget(title)

        splitter = QSplitter(Qt.Horizontal)

        # ===== Левая панель: исходные данные =====
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Объект
        obj_box = QGroupBox("Объект")
        obj_form = QFormLayout(obj_box)
        self.ed_object = QLineEdit()
        self.ed_object.setPlaceholderText("Название объекта")
        self.ed_customer = QLineEdit()
        self.ed_customer.setPlaceholderText("Заказчик")
        self.spin_area = QDoubleSpinBox()
        self.spin_area.setRange(0, 1_000_000)
        self.spin_area.setValue(100.0)
        self.spin_area.setSuffix(" м²")
        self.spin_area.setDecimals(2)
        self.spin_elements = QSpinBox()
        self.spin_elements.setRange(1, 10_000)
        self.spin_elements.setValue(1)
        self.spin_area_el = QDoubleSpinBox()
        self.spin_area_el.setRange(0, 100_000)
        self.spin_area_el.setSuffix(" м²")
        obj_form.addRow("Объект:", self.ed_object)
        obj_form.addRow("Заказчик:", self.ed_customer)
        obj_form.addRow("Площадь:", self.spin_area)
        obj_form.addRow("Кол-во элементов:", self.spin_elements)
        obj_form.addRow("Площадь элемента:", self.spin_area_el)
        left_layout.addWidget(obj_box)

        # Условия
        cond_box = QGroupBox("Условия эксплуатации")
        cond_form = QFormLayout(cond_box)
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
        self.spin_losses = QDoubleSpinBox()
        self.spin_losses.setRange(0, 99)
        self.spin_losses.setValue(0)
        self.spin_losses.setSuffix(" %")
        cond_form.addRow("Категория:", self.cmb_corrosion)
        cond_form.addRow("Долговечность:", self.cmb_durability)
        cond_form.addRow("Поверхность:", self.cmb_surface)
        cond_form.addRow("Среда:", self.cmb_environment)
        cond_form.addRow("T мин:", self.spin_tmin)
        cond_form.addRow("T макс:", self.spin_tmax)
        cond_form.addRow("Потери по умолч.:", self.spin_losses)
        left_layout.addWidget(cond_box)
        left_layout.addStretch()

        splitter.addWidget(left)

        # ===== Правая панель: слои + результат =====
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Добавление слоя
        add_box = QGroupBox("Слои системы")
        add_layout = QVBoxLayout(add_box)

        row_add = QHBoxLayout()
        self.cmb_material = QComboBox()
        self.cmb_material.setMinimumWidth(200)
        self.spin_dft = QDoubleSpinBox()
        self.spin_dft.setRange(1, 2000)
        self.spin_dft.setValue(100)
        self.spin_dft.setSuffix(" мкм")
        self.spin_layer_losses = QDoubleSpinBox()
        self.spin_layer_losses.setRange(0, 99)
        self.spin_layer_losses.setValue(0)
        self.spin_layer_losses.setSuffix(" %")
        self.spin_thinner = QDoubleSpinBox()
        self.spin_thinner.setRange(0, 100)
        self.spin_thinner.setValue(0)
        self.spin_thinner.setSuffix(" %")
        btn_add = QPushButton("Добавить слой")
        btn_add.clicked.connect(self._on_add_layer)
        btn_remove = QPushButton("Удалить")
        btn_remove.setProperty("secondary", True)
        btn_remove.clicked.connect(self._on_remove_layer)
        btn_clear = QPushButton("Очистить")
        btn_clear.setProperty("secondary", True)
        btn_clear.clicked.connect(self._on_clear_layers)

        row_add.addWidget(QLabel("Материал:"))
        row_add.addWidget(self.cmb_material, 1)
        row_add.addWidget(QLabel("DFT:"))
        row_add.addWidget(self.spin_dft)
        row_add.addWidget(QLabel("Потери:"))
        row_add.addWidget(self.spin_layer_losses)
        row_add.addWidget(QLabel("Разб.:"))
        row_add.addWidget(self.spin_thinner)
        row_add.addWidget(btn_add)
        row_add.addWidget(btn_remove)
        row_add.addWidget(btn_clear)
        add_layout.addLayout(row_add)

        self.layer_table = LayerTableWidget()
        add_layout.addWidget(self.layer_table)
        right_layout.addWidget(add_box)

        # Кнопки расчёта
        btn_row = QHBoxLayout()
        self.btn_calc = QPushButton("Рассчитать")
        self.btn_calc.clicked.connect(self._on_calculate)
        self.btn_demo = QPushButton("Демо-система")
        self.btn_demo.setProperty("secondary", True)
        self.btn_demo.clicked.connect(self._on_load_demo)
        self.btn_excel = QPushButton("Excel")
        self.btn_excel.setProperty("secondary", True)
        self.btn_excel.clicked.connect(self._on_export_excel)
        self.btn_excel.setEnabled(False)
        self.btn_pdf = QPushButton("PDF")
        self.btn_pdf.setProperty("secondary", True)
        self.btn_pdf.clicked.connect(self._on_export_pdf)
        self.btn_pdf.setEnabled(False)
        self.btn_to_cmp = QPushButton("В сравнение")
        self.btn_to_cmp.setProperty("secondary", True)
        self.btn_to_cmp.clicked.connect(self._on_to_comparison)
        self.btn_to_cmp.setEnabled(False)
        btn_row.addWidget(self.btn_calc)
        btn_row.addWidget(self.btn_demo)
        btn_row.addWidget(self.btn_excel)
        btn_row.addWidget(self.btn_pdf)
        btn_row.addWidget(self.btn_to_cmp)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        # Результат
        res_box = QGroupBox("Результат")
        res_layout = QVBoxLayout(res_box)
        self.lbl_summary = QLabel("Выполните расчёт")
        self.lbl_summary.setProperty("subheading", True)
        self.lbl_summary.setWordWrap(True)
        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setMaximumHeight(180)
        res_layout.addWidget(self.lbl_summary)
        res_layout.addWidget(self.txt_details)
        right_layout.addWidget(res_box)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter)

    # ------------------------------------------------------------------
    def set_materials(self, materials: list[Material]) -> None:
        self._materials = [m for m in materials if m.material_type != MaterialType.THINNER]
        self.cmb_material.clear()
        for m in self._materials:
            self.cmb_material.addItem(m.display_name(), m)

    def _current_material(self) -> Optional[Material]:
        return self.cmb_material.currentData()

    def _build_object_data(self) -> ObjectData:
        area = self.spin_area.value()
        if area <= 0 and self.spin_area_el.value() > 0:
            area = self.spin_area_el.value() * self.spin_elements.value()
        return ObjectData(
            object_name=self.ed_object.text().strip(),
            customer=self.ed_customer.text().strip(),
            area_m2=area,
            elements_count=self.spin_elements.value(),
            area_per_element=self.spin_area_el.value(),
            corrosion_category=self.cmb_corrosion.currentData(),
            durability=self.cmb_durability.currentData(),
            surface_type=self.cmb_surface.currentData(),
            environment=self.cmb_environment.currentData(),
            temperature_min=self.spin_tmin.value(),
            temperature_max=self.spin_tmax.value(),
        )

    def _on_add_layer(self) -> None:
        mat = self._current_material()
        if mat is None:
            QMessageBox.warning(self, "Внимание", "Выберите материал")
            return
        li = LayerInput(
            material=mat,
            target_dft=self.spin_dft.value(),
            losses_percent=self.spin_layer_losses.value(),
            thinner_percent=self.spin_thinner.value(),
        )
        self.layer_table.add_layer(li)

    def _on_remove_layer(self) -> None:
        self.layer_table.remove_selected()

    def _on_clear_layers(self) -> None:
        self.layer_table.clear_layers()
        self.lbl_summary.setText("Выполните расчёт")
        self.txt_details.clear()

    def _on_load_demo(self) -> None:
        """Загрузить демо-систему Blank Universal + Finish."""
        if len(self._materials) < 2:
            # Создаём демо-материалы на лету
            primer = Material(
                manufacturer="Blank", brand="Blank",
                material_name="Грунт-Эмаль Blank Universal",
                material_type=MaterialType.PRIMER_ENAMEL,
                binder_type=BinderType.EPOXY,
                density=1.4, solids_percent=73.0, price_per_kg=552.0,
                recommended_dft_min=100, recommended_dft_max=200, packaging_kg=20.0,
            )
            finish = Material(
                manufacturer="Blank", brand="Blank",
                material_name="Эмаль Blank Finish",
                material_type=MaterialType.FINISH,
                binder_type=BinderType.POLYURETHANE,
                density=1.3, solids_percent=58.0, price_per_kg=892.0,
                recommended_dft_min=60, recommended_dft_max=100, packaging_kg=20.0,
            )
            self.set_materials([primer, finish])
        else:
            primer = self._materials[0]
            finish = self._materials[1] if len(self._materials) > 1 else self._materials[0]

        self.layer_table.clear_layers()
        self.layer_table.add_layer(LayerInput(material=primer, target_dft=200, losses_percent=5, thinner_percent=5))
        self.layer_table.add_layer(LayerInput(material=finish, target_dft=80, losses_percent=5, thinner_percent=5))
        self.ed_object.setText("Резервуар РВС-1000 (демо)")
        self.ed_customer.setText("ООО Пример")
        self.spin_area.setValue(1250)
        self.cmb_corrosion.setCurrentIndex(self.cmb_corrosion.findData(CorrosionCategory.C4))
        self.cmb_durability.setCurrentIndex(self.cmb_durability.findData(DurabilityLevel.HIGH))

    def _on_calculate(self) -> None:
        layers = self.layer_table.get_layer_inputs()
        if not layers:
            QMessageBox.warning(self, "Внимание", "Добавьте хотя бы один слой")
            return

        obj = self._build_object_data()
        # Применить потери по умолчанию, если у слоя 0
        default_losses = self.spin_losses.value()
        for li in layers:
            if li.losses_percent == 0 and default_losses > 0:
                li.losses_percent = default_losses

        result, validation = self.service.calculate_system(obj, layers)
        self._last_result = result

        if validation.has_errors:
            msgs = "\n".join(f"• {e.message}" for e in validation.errors)
            QMessageBox.critical(self, "Ошибки валидации", msgs)
            return

        if validation.has_warnings:
            msgs = "\n".join(f"• {w.message}" for w in validation.warnings)
            QMessageBox.warning(self, "Предупреждения", msgs)

        # Обновить таблицу с результатами
        self.layer_table.set_layers(layers, result.layers)

        self.lbl_summary.setText(
            f"Толщина: {result.total_dft:.0f} мкм  |  "
            f"Расход: {result.total_practical_consumption_kg:.3f} кг/м²  |  "
            f"Стоимость: {result.total_cost_per_m2:.2f} руб/м²  |  "
            f"Объект: {result.total_cost:,.0f} руб".replace(",", " ")
        )
        self.txt_details.setPlainText(self.service.format_summary(result))
        self.btn_excel.setEnabled(True)
        self.btn_pdf.setEnabled(True)
        self.btn_to_cmp.setEnabled(True)
        self.calculation_done.emit(result)