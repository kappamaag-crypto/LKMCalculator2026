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
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.repositories import MaterialRepository


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
        self.spin_density.setSpecialValueText("не задано")
        self.spin_density.setValue(material.density if material and material.density is not None else 0)

        self.spin_solids = QDoubleSpinBox()
        self.spin_solids.setRange(0, 100)
        self.spin_solids.setDecimals(2)
        self.spin_solids.setSpecialValueText("не задано")
        self.spin_solids.setValue(material.solids_percent if material and material.solids_percent is not None else 0)

        self.spin_price_kg = QDoubleSpinBox()
        self.spin_price_kg.setRange(0, 1_000_000)
        self.spin_price_kg.setDecimals(2)
        self.spin_price_kg.setSpecialValueText("не задано")
        self.spin_price_kg.setValue(material.price_per_kg if material and material.price_per_kg is not None else 0)

        self.spin_price_liter = QDoubleSpinBox()
        self.spin_price_liter.setRange(0, 1_000_000)
        self.spin_price_liter.setDecimals(2)
        self.spin_price_liter.setSpecialValueText("не задано")
        self.spin_price_liter.setValue(material.price_per_liter if material and material.price_per_liter is not None else 0)

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
        layout.addRow("Цена, руб/кг:", self.spin_price_kg)
        layout.addRow("Цена, руб/л:", self.spin_price_liter)
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
            density=self.spin_density.value() or None,
            solids_percent=self.spin_solids.value() or None,
            price_per_kg=self.spin_price_kg.value() or None,
            price_per_liter=self.spin_price_liter.value() or None,
            recommended_dft_min=self.spin_dft_min.value() or None,
            recommended_dft_max=self.spin_dft_max.value() or None,
            is_active=True,
        )


class MaterialsView(QWidget):
    """База ЛКМ — просмотр и редактирование с сохранением в SQLite."""

    materials_changed = Signal(list)

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
        btn_row.addWidget(btn_add); btn_row.addWidget(btn_edit); btn_row.addWidget(btn_del); btn_row.addStretch()
        root.addLayout(btn_row)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Производитель", "Тип", "Связующее", "Плотность", "СО, %", "Цена, руб/кг", "Цена, руб/л"])
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
        return [m for m in self._materials if q in f"{m.material_name} {m.manufacturer} {m.brand} {m.binder_type}".lower()]

    def _reload_table(self) -> None:
        rows = self._filtered()
        self.table.setRowCount(len(rows))
        for r, m in enumerate(rows):
            vals = [str(m.id or ""), m.material_name, m.manufacturer or "—", m.material_type.value if hasattr(m.material_type, "value") else str(m.material_type), m.binder_type.value if hasattr(m.binder_type, "value") else str(m.binder_type), f"{m.density:.2f}" if m.density is not None else "—", f"{m.solids_percent:.0f}" if m.solids_percent is not None else "—", f"{m.price_per_kg:.0f}" if m.price_per_kg is not None else "—", f"{m.price_per_liter:.0f}" if m.price_per_liter is not None else "—"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v); item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 0: item.setData(Qt.UserRole, m.id)
                self.table.setItem(r, c, item)
        self.lbl_count.setText(f"Материалов: {len(rows)} (всего {len(self._materials)})")

    def _selected_material(self) -> Optional[Material]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        mid = item.data(Qt.UserRole) if item else None
        return next((m for m in self._materials if m.id == mid), None)

    @staticmethod
    def _save_if_missing(material: Material) -> Material:
        with get_session_factory()() as session:
            repo = MaterialRepository(session)
            existing = repo.get_by_name(material.material_name)
            if existing is not None:
                return existing
            saved = repo.add(material)
            session.commit()
            return saved

    def _on_add(self) -> None:
        dlg = MaterialEditDialog(parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        mat = dlg.get_material()
        if not mat.material_name:
            QMessageBox.warning(self, "Ошибка", "Укажите название")
            return
        try:
            saved = self._save_if_missing(mat)
        except Exception as exc:
            QMessageBox.critical(self, "База данных", f"Не удалось сохранить материал:\n{exc}")
            return
        existing_idx = next((i for i, m in enumerate(self._materials) if m.material_name.casefold() == saved.material_name.casefold()), None)
        if existing_idx is None:
            self._materials.append(saved)
        else:
            self._materials[existing_idx] = saved
        self._next_id = max(self._next_id, (saved.id or 0) + 1)
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
        try:
            with get_session_factory()() as session:
                repo = MaterialRepository(session)
                db_mat = repo.get_by_id(mat.id) if mat.id is not None else None
                if db_mat is None:
                    db_mat = repo.get_by_name(mat.material_name)
                if db_mat is None:
                    saved = repo.add(updated)
                else:
                    updated.id = db_mat.id
                    saved = repo.update(updated)
                session.commit()
        except Exception as exc:
            QMessageBox.critical(self, "База данных", f"Не удалось сохранить изменения:\n{exc}")
            return
        for i, m in enumerate(self._materials):
            if m.id == mat.id:
                self._materials[i] = saved
                break
        else:
            self._materials.append(saved)
        self._reload_table()
        self.materials_changed.emit(self.get_materials())

    def _on_delete(self) -> None:
        mat = self._selected_material()
        if mat is None:
            return
        if QMessageBox.question(self, "Удаление", f"Удалить «{mat.material_name}»?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            if mat.id is not None:
                with get_session_factory()() as session:
                    MaterialRepository(session).delete(mat.id, soft=True)
                    session.commit()
        except Exception as exc:
            QMessageBox.critical(self, "База данных", f"Не удалось удалить материал:\n{exc}")
            return
        self._materials = [m for m in self._materials if m.id != mat.id]
        self._reload_table()
        self.materials_changed.emit(self.get_materials())
