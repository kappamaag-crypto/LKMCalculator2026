"""Диалог быстрого добавления материала непосредственно в расчёт.

Материал не сохраняется в БД: он существует только в текущем расчёте.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QLineEdit, QVBoxLayout, QMessageBox, QCheckBox
)

from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material


class AdHocMaterialDialog(QDialog):
    """Создание временного материала для текущего расчёта."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить материал в расчёт")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        basic = QGroupBox("Основные данные")
        form = QFormLayout(basic)
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Например: ЭФФА ЭП-150")
        self.ed_manufacturer = QLineEdit()
        self.ed_manufacturer.setPlaceholderText("Необязательно")
        self.ed_brand = QLineEdit()
        self.ed_brand.setPlaceholderText("Необязательно")
        self.cmb_type = QComboBox()
        for value in MaterialType:
            if value != MaterialType.THINNER:
                self.cmb_type.addItem(value.value, value)
        self.cmb_binder = QComboBox()
        for value in BinderType:
            self.cmb_binder.addItem(value.value, value)
        self.chk_two_component = QCheckBox("Двухкомпонентный материал")
        form.addRow("Название*:", self.ed_name)
        form.addRow("Производитель:", self.ed_manufacturer)
        form.addRow("Бренд:", self.ed_brand)
        form.addRow("Тип:", self.cmb_type)
        form.addRow("Связующее:", self.cmb_binder)
        form.addRow(":", self.chk_two_component)
        root.addWidget(basic)

        calc = QGroupBox("Параметры для расчёта")
        cf = QFormLayout(calc)
        self.spin_density = self._spin(0.01, 10.0, 3, 1.0, " кг/л")
        self.spin_solids = self._spin(0.01, 100.0, 2, 70.0, " %")
        self.spin_price = self._spin(0.0, 1000000.0, 2, 0.0, " ₽/кг")
        self.spin_dft_min = self._spin(0.0, 2000.0, 0, 0.0, " мкм")
        self.spin_dft_max = self._spin(0.0, 2000.0, 0, 0.0, " мкм")
        self.spin_hard_max = self._spin(0.0, 2000.0, 0, 0.0, " мкм")
        cf.addRow("Плотность*:", self.spin_density)
        cf.addRow("Сухой остаток по объёму*:", self.spin_solids)
        cf.addRow("Цена:", self.spin_price)
        cf.addRow("Рекомендуемый DFT от:", self.spin_dft_min)
        cf.addRow("Рекомендуемый DFT до:", self.spin_dft_max)
        cf.addRow("Жёсткий максимум DFT:", self.spin_hard_max)
        root.addWidget(calc)

        note = QGroupBox("Важно")
        nf = QFormLayout(note)
        note_text = QLineEdit("Материал не записывается в базу данных и доступен только в текущем расчёте.")
        note_text.setReadOnly(True)
        note_text.setFrame(False)
        nf.addRow(note_text)
        root.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _spin(minimum, maximum, decimals, value, suffix):
        box = QDoubleSpinBox()
        box.setRange(minimum, maximum)
        box.setDecimals(decimals)
        box.setValue(value)
        box.setSuffix(suffix)
        box.setKeyboardTracking(False)
        return box

    def _accept(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Материал", "Укажите название материала.")
            self.ed_name.setFocus()
            return
        if self.spin_dft_max.value() and self.spin_dft_min.value() > self.spin_dft_max.value():
            QMessageBox.warning(self, "Материал", "Рекомендуемый DFT от не может быть больше DFT до.")
            return
        self.accept()

    def material(self) -> Material:
        min_dft = self.spin_dft_min.value() or None
        max_dft = self.spin_dft_max.value() or None
        hard_max = self.spin_hard_max.value() or None
        price = self.spin_price.value() or None
        return Material(
            manufacturer=self.ed_manufacturer.text().strip(),
            brand=self.ed_brand.text().strip(),
            material_name=self.ed_name.text().strip(),
            material_type=self.cmb_type.currentData() or MaterialType.OTHER,
            binder_type=self.cmb_binder.currentData() or BinderType.UNKNOWN,
            density=self.spin_density.value(),
            solids_by_volume_percent=self.spin_solids.value(),
            price_per_kg=price,
            recommended_dft_min=min_dft,
            recommended_dft_max=max_dft,
            max_single_layer_dft=hard_max,
            is_two_component=self.chk_two_component.isChecked(),
            is_active=True,
            is_incomplete=False,
        )
