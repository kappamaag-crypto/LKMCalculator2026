"""Вкладка базы материалов (просмотр + простой CRUD)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QLineEdit, QFormLayout, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QComboBox,
)
from PySide6.QtCore import Qt, Signal

from app.domain.models import Material
from app.domain.enums import MaterialType, BinderType


class MaterialEditDialog(QDialog):
    def __init__(self, material: Optional[Material] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Материал" if material else "Новый материал")
        self.setMinimumWidth(400)
        self.material = material
        layout = QFormLayout(self)

        self.ed_name = QLineEdit(material.material_name if material else "")
        self.ed_manufacturer = QLineEdit(material.manufacturer if material else "")
        self.ed_brand = QLineEdit(material.brand if material else "")
        self.cmb_type = QComboBox()
        for t in MaterialType:
            self.cmb_type.addItem(t.value, t)
        if material:
            idx = self.cmb_type.findData(material.material_type)
            if idx >= 0:
                self.cmb_type.setCurrentIndex(idx)
        self.cmb_binder = QComboBox()
        for b in BinderType:
            self.cmb_binder.addItem(b.value, b)
        if material:
            idx = self.cmb_binder.findData(material.binder_type)
            if idx >= 0:
                self.cmb_binder.setCurrentIndex(idx)
        self.spin_density = QDoubleSpinBox()
        self.spin_density.setRange(0, 10)
        self.spin_density.setDecimals(3)
        self.spin_density.setValue(material.density if material else 1.3)
        self.spin_solids = QDoubleSpinBox()
        self.spin_solids.setRange(0, 100)
        self.spin_solids.setValue(material.solids_percent if material else 60)
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 1_000_000)
        self.spin_price.setDecimals(2)
        self.spin_price.setValue(material.price_per_kg or 0 if material else 0)
        self.spin_pack = QDoubleSpinBox()
        self.spin_pack.setRange(0, 1000)
        self.spin_pack.setValue(material.packaging_kg or 20 if material else 20)
        self.spin_dft_min = QDoubleSpinBox()
        self.spin_dft_min.setRange(0, 2000)
        self.spin_dft_min.setValue(material.recommended_dft_min or 0 if material else 0)
        self.spin_dft_max = QDoubleSpinBox()
        self.spin_dft_max.setRange(0, 2000)
        self.spin_dft_max.setValue(material.recommended_dft_max or 0 if material else 0)

        layout.addRow("Название*:", self.ed_name)
        layout.addRow("Производитель:", self.ed_manufacturer)
        layout.addRow("Бренд:", self.ed_brand)
        layout.addRow("Тип:", self.cmb_type)
        layout.addRow("Связующее:", self.cmb_binder)
        layout.addRow("Плотность, кг/л:", self.spin_density)
        layout.addRow("Сухой остаток, %:", self.spin_solids)
        layout.addRow("Цена, руб/кг:", self.spin_price)
        layout.addRow("Фасовка, кг:", self.spin_pack)
        layout.addRow("DFT min, мкм:", self.spin_dft_min)
        layout.addRow("DFT max, мкм:", self.spin_dft_max)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_material(self) -> Material:
        base = self.material or Material()
        return Material(
            id=base.id,
            material_name=self.ed_name.text().strip(),
            manufacturer=self.ed_manufacturer.text().strip(),
            brand=self.ed_brand.text().strip(),
            material_type=self.cmb_type.currentData() or MaterialType.OTHER,
            binder_type=self.cmb_binder.currentData() or BinderType.UNKNOWN,
            density=self.spin_density.value(),
            solids_percent=self.spin_solids.value(),
            price_per_kg=self.spin_price.value() or None,
            packaging_kg=self.spin_pack.value() or None,
            recommended_dft_min=self.spin_dft_min.value() or None,
            recommended_dft_max=self.spin_dft_max.value() or None,
            is_active=True,
        )


class MaterialsView(QWidget):
    """База ЛКМ — просмотр и редактирование."""

    materials_changed = Signal(list)  # list[Material]

    def __init__(self, materials: list[Material] | None = None, parent=None):
        super().__init__(parent)
        self._materials: list[Material] = list(materials or [])
        self._next_id = max((m.id or 0 for m in self._materials), default=0) + 1
        self._build_ui()
        self._reload_table()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("База материалов")
        title.setProperty("heading", True)
        root.addWidget(title)

        search_row = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("Поиск: название, производитель, связующее…")
        self.ed_search.textChanged.connect(self._reload_table)
        search_row.addWidget(self.ed_search)
        root.addLayout(search_row)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Добавить")
        btn_add.clicked.connect(self._on_add)
        btn_edit = QPushButton("Изменить")
        btn_edit.setProperty("secondary", True)
        btn_edit.clicked.connect(self._on_edit)
        btn_del = QPushButton("Удалить")
        btn_del.setProperty("secondary", True)
        btn_del.clicked.connect(self._on_delete)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Название", "Производитель", "Тип", "Связующее",
            "Плотность", "СО, %", "Цена, руб/кг",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.doubleClicked.connect(self._on_edit)
        root.addWidget(self.table)

        self.lbl_count = QLabel()
        root.addWidget(self.lbl_count)

    def set_materials(self, materials: list[Material]) -> None:
        self._materials = list(materials)
        self._next_id = max((m.id or 0 for m in self._materials), default=0) + 1
        self._reload_table()

    def get_materials(self) -> list[Material]:
        return list(self._materials)

    def _filtered(self) -> list[Material]:
        q = self.ed_search.text().strip().lower()
        if not q:
            return self._materials
        result = []
        for m in self._materials:
            hay = f"{m.material_name} {m.manufacturer} {m.brand} {m.binder_type}".lower()
            if q in hay:
                result.append(m)
        return result

    def _reload_table(self) -> None:
        rows = self._filtered()
        self.table.setRowCount(len(rows))
        for r, m in enumerate(rows):
            vals = [
                str(m.id or ""),
                m.material_name,
                m.manufacturer or "—",
                m.material_type.value if hasattr(m.material_type, "value") else str(m.material_type),
                m.binder_type.value if hasattr(m.binder_type, "value") else str(m.binder_type),
                f"{m.density:.2f}",
                f"{m.solids_percent:.0f}",
                f"{m.price_per_kg:.0f}" if m.price_per_kg else "—",
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 0:
                    item.setData(Qt.UserRole, m.id)
                self.table.setItem(r, c, item)
        self.lbl_count.setText(f"Материалов: {len(rows)} (всего {len(self._materials)})")

    def _selected_material(self) -> Optional[Material]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        mid = item.data(Qt.UserRole) if item else None
        for m in self._materials:
            if m.id == mid:
                return m
        return None

    def _on_add(self) -> None:
        dlg = MaterialEditDialog(parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        mat = dlg.get_material()
        if not mat.material_name:
            QMessageBox.warning(self, "Ошибка", "Укажите название")
            return
        mat.id = self._next_id
        self._next_id += 1
        self._materials.append(mat)
        self._reload_table()
        self.materials_changed.emit(self.get_materials())

    def _on_edit(self) -> None:
        mat = self._selected_material()
        if mat is None:
            QMessageBox.information(self, "База", "Выберите материал")
            return
        dlg = MaterialEditDialog(mat, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        updated = dlg.get_material()
        if not updated.material_name:
            QMessageBox.warning(self, "Ошибка", "Укажите название")
            return
        for i, m in enumerate(self._materials):
            if m.id == mat.id:
                self._materials[i] = updated
                break
        self._reload_table()
        self.materials_changed.emit(self.get_materials())

    def _on_delete(self) -> None:
        mat = self._selected_material()
        if mat is None:
            return
        if QMessageBox.question(
            self, "Удаление", f"Удалить «{mat.material_name}»?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self._materials = [m for m in self._materials if m.id != mat.id]
        self._reload_table()
        self.materials_changed.emit(self.get_materials())
