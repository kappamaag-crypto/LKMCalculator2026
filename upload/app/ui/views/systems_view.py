"""Редактор сохранённых систем покрытия."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QTextEdit,
)
from PySide6.QtCore import Signal
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.models import Material
from app.domain.enums import MaterialType, CompatibilityStatus
from app.domain.layer_compatibility import LayerCompatibilityEngine
from app.domain.models import LayerDefinition
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.models import CoatingSystemORM, CoatingSystemLayerORM
from app.infrastructure.database.repositories import CoatingSystemRepository


class SystemsView(QWidget):
    systems_changed = Signal()

    def __init__(self, materials: list[Material], parent=None):
        super().__init__(parent)
        self._materials = list(materials)
        self._systems = []
        self._current_id = None
        self._calculation_result = None
        self._compatibility = LayerCompatibilityEngine()
        self._build_ui()
        self.set_materials(materials)
        self.reload()

    @staticmethod
    def _material_type_value(material: Material) -> str:
        value = getattr(material, "material_type", "")
        return value.value if isinstance(value, MaterialType) else str(value or "")

    def _build_ui(self):
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.list_systems = QComboBox()
        self.list_systems.setMinimumWidth(420)
        self.list_systems.currentIndexChanged.connect(self._load_selected)
        self.btn_new = QPushButton("Новая система")
        self.btn_new.clicked.connect(self._new)
        self.btn_copy = QPushButton("Копировать")
        self.btn_copy.setToolTip("Создать новый несохранённый черновик из выбранной системы")
        self.btn_copy.clicked.connect(self._copy_selected)
        self.btn_from_calculation = QPushButton("Из текущего расчёта")
        self.btn_from_calculation.setToolTip("Создать несохранённый черновик системы из последнего расчёта")
        self.btn_from_calculation.clicked.connect(self._from_calculation)
        self.btn_reload = QPushButton("Обновить")
        self.btn_reload.setProperty("secondary", True)
        self.btn_reload.clicked.connect(self.reload)
        top.addWidget(QLabel("Система:"))
        top.addWidget(self.list_systems, 1)
        top.addWidget(self.btn_new)
        top.addWidget(self.btn_copy)
        top.addWidget(self.btn_from_calculation)
        top.addWidget(self.btn_reload)
        root.addLayout(top)

        info = QGroupBox("Параметры системы")
        form = QFormLayout(info)
        self.ed_name = QLineEdit()
        self.ed_manufacturer = QLineEdit()
        self.ed_description = QLineEdit()
        self.ed_substrate = QLineEdit()
        self.ed_standards = QLineEdit()
        self.ed_certificate = QLineEdit()
        form.addRow("Название:", self.ed_name)
        form.addRow("Производитель:", self.ed_manufacturer)
        form.addRow("Описание:", self.ed_description)
        form.addRow("Основание:", self.ed_substrate)
        form.addRow("Нормативы:", self.ed_standards)
        form.addRow("Сертификат:", self.ed_certificate)
        root.addWidget(info)

        layerbox = QGroupBox("Слои системы")
        lv = QVBoxLayout(layerbox)
        buttons = QHBoxLayout()
        self.cmb_material = QComboBox()
        self.cmb_material.setMinimumWidth(380)
        self.btn_add_layer = QPushButton("Добавить слой")
        self.btn_add_layer.clicked.connect(self._add_layer)
        self.btn_del_layer = QPushButton("Удалить слой")
        self.btn_del_layer.setProperty("secondary", True)
        self.btn_del_layer.clicked.connect(self._delete_layer)
        self.btn_up_layer = QPushButton("↑")
        self.btn_up_layer.setToolTip("Переместить слой вверх")
        self.btn_up_layer.clicked.connect(lambda: self._move_layer(-1))
        self.btn_down_layer = QPushButton("↓")
        self.btn_down_layer.setToolTip("Переместить слой вниз")
        self.btn_down_layer.clicked.connect(lambda: self._move_layer(1))
        buttons.addWidget(QLabel("Материал:"))
        buttons.addWidget(self.cmb_material)
        buttons.addWidget(self.btn_add_layer)
        buttons.addWidget(self.btn_del_layer)
        buttons.addWidget(self.btn_up_layer)
        buttons.addWidget(self.btn_down_layer)
        buttons.addStretch()
        lv.addLayout(buttons)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "№", "Материал", "DFT мин, мкм", "DFT целевой, мкм",
            "DFT макс, мкм", "Разбавитель, %",
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemChanged.connect(self._renumber)
        self.table.itemChanged.connect(self._refresh_compatibility)
        lv.addWidget(self.table)
        root.addWidget(layerbox, 1)

        compatibility_box = QGroupBox("Совместимость соседних слоёв")
        compatibility_layout = QVBoxLayout(compatibility_box)
        self.lbl_compatibility_status = QLabel("UNKNOWN — добавьте минимум два слоя")
        self.lbl_compatibility_status.setWordWrap(True)
        compatibility_layout.addWidget(self.lbl_compatibility_status)
        self.txt_compatibility = QTextEdit()
        self.txt_compatibility.setReadOnly(True)
        self.txt_compatibility.setMinimumHeight(80)
        compatibility_layout.addWidget(self.txt_compatibility)
        note = QLabel(
            "Проверка использует только source-backed матрицу совместимости. "
            "UNKNOWN не является запретом; условия отверждения/окна перекрытия "
            "по TDS здесь не выводятся."
        )
        note.setWordWrap(True)
        compatibility_layout.addWidget(note)
        root.addWidget(compatibility_box)

        bottom = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить систему")
        self.btn_save.clicked.connect(self._save)
        self.btn_delete = QPushButton("Удалить систему")
        self.btn_delete.setProperty("secondary", True)
        self.btn_delete.clicked.connect(self._delete_system)
        bottom.addWidget(self.btn_save)
        bottom.addWidget(self.btn_delete)
        bottom.addStretch()
        bottom.addWidget(QLabel("Изменения применяются к базе только после сохранения."))
        root.addLayout(bottom)

    def set_materials(self, materials: list[Material]):
        self._materials = list(materials)
        self.cmb_material.clear()
        for material in self._materials:
            if self._material_type_value(material) != MaterialType.THINNER.value:
                self.cmb_material.addItem(material.display_name(), material)

    def set_calculation_result(self, result):
        self._calculation_result = result
        self.btn_from_calculation.setEnabled(result is not None and bool(getattr(result, "layers", None)))

    def _copy_selected(self):
        sid = self.list_systems.currentData()
        orm = next((item for item in self._systems if item.id == sid), None)
        if orm is None:
            QMessageBox.warning(self, "Система", "Выберите сохранённую систему для копирования")
            return

        self._current_id = None
        self.list_systems.blockSignals(True)
        self.list_systems.setCurrentIndex(0)
        self.list_systems.blockSignals(False)
        self.ed_name.setText(f"{orm.system_name or 'Пользовательская система'} — копия")
        self.ed_manufacturer.setText(orm.manufacturer or "")
        self.ed_description.setText(orm.description or "")
        self.ed_substrate.setText(orm.substrate or "")
        self.ed_standards.setText(orm.standards or "")
        self.ed_certificate.setText(orm.certificate or "")

        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for layer in sorted(orm.layers, key=lambda item: item.layer_number):
            material = next((m for m in self._materials if m.id == layer.material_id), None)
            self._append_row(
                layer.layer_number,
                material,
                layer.dft_min,
                layer.target_dft,
                layer.dft_max,
                layer.thinner_percent,
            )
        self.table.blockSignals(False)
        if self.table.rowCount():
            self.table.selectRow(0)
        self._refresh_compatibility()
        self.status_message(f"Создан черновик копии системы: {self.table.rowCount()} слоёв. Проверьте и сохраните его.")

    def _from_calculation(self):
        result = self._calculation_result
        if result is None or not result.layers:
            QMessageBox.warning(self, "Система", "Сначала выполните расчёт с хотя бы одним слоем")
            return

        system = getattr(result, "system", None)
        self._current_id = None
        self.list_systems.blockSignals(True)
        self.list_systems.setCurrentIndex(0)
        self.list_systems.blockSignals(False)
        self.ed_name.setText((getattr(system, "system_name", "") or "Пользовательская система") + " — из расчёта")
        self.ed_manufacturer.setText(getattr(system, "manufacturer", "") or "")
        self.ed_description.setText(getattr(system, "description", "") or "Создано из расчёта")
        self.ed_substrate.setText(getattr(system, "substrate", "") or "")
        self.ed_standards.setText(getattr(system, "standards", "") or "")
        self.ed_certificate.setText(getattr(system, "certificate", "") or "")

        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for number, layer in enumerate(result.layers, start=1):
            self._append_row(
                number,
                layer.material,
                None,
                layer.target_dft,
                None,
                layer.thinner_percent,
            )
        self.table.blockSignals(False)
        self.table.selectRow(0)
        self._refresh_compatibility()
        self.status_message(f"Создан черновик системы из расчёта: {len(result.layers)} слоёв. Проверьте и сохраните его.")

    def status_message(self, text):
        parent = self.window()
        if hasattr(parent, "statusBar"):
            parent.statusBar().showMessage(text, 10000)

    def reload(self):
        try:
            with get_session_factory()() as session:
                stmt = (
                    select(CoatingSystemORM)
                    .options(selectinload(CoatingSystemORM.layers))
                    .where(CoatingSystemORM.is_active.is_(True))
                    .order_by(CoatingSystemORM.system_name)
                )
                self._systems = list(session.scalars(stmt).unique().all())
        except Exception as exc:
            self._systems = []
            QMessageBox.warning(self, "База систем", f"Не удалось загрузить системы: {exc}")
            return

        self.list_systems.blockSignals(True)
        self.list_systems.clear()
        self.list_systems.addItem("— новая система —", None)
        for system in self._systems:
            self.list_systems.addItem(system.system_name, system.id)
        self.list_systems.blockSignals(False)

        if self._current_id is not None:
            idx = self.list_systems.findData(self._current_id)
            self.list_systems.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self._new()

    def _new(self):
        self._current_id = None
        self.list_systems.blockSignals(True)
        self.list_systems.setCurrentIndex(0)
        self.list_systems.blockSignals(False)
        self.ed_name.clear()
        self.ed_manufacturer.clear()
        self.ed_description.clear()
        self.ed_substrate.clear()
        self.ed_standards.clear()
        self.ed_certificate.clear()
        self.table.setRowCount(0)
        self._refresh_compatibility()

    def _load_selected(self, index):
        sid = self.list_systems.itemData(index)
        if sid is None:
            if self._current_id is not None:
                self._new()
            return

        orm = next((item for item in self._systems if item.id == sid), None)
        if orm is None:
            return

        self._current_id = sid
        self.ed_name.setText(orm.system_name or "")
        self.ed_manufacturer.setText(orm.manufacturer or "")
        self.ed_description.setText(orm.description or "")
        self.ed_substrate.setText(orm.substrate or "")
        self.ed_standards.setText(orm.standards or "")
        self.ed_certificate.setText(orm.certificate or "")
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for layer in sorted(orm.layers, key=lambda item: item.layer_number):
            material = next((m for m in self._materials if m.id == layer.material_id), None)
            self._append_row(
                layer.layer_number,
                material,
                layer.dft_min,
                layer.target_dft,
                layer.dft_max,
                layer.thinner_percent,
            )
        self.table.blockSignals(False)
        self._refresh_compatibility()

    def _append_row(self, num, material, dmin, target, dmax, thinner):
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [
            str(num),
            material.display_name() if material else "Материал не найден",
            self._num(dmin),
            self._num(target),
            self._num(dmax),
            self._num(thinner, 2),
        ]
        for col, value in enumerate(values):
            self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.item(row, 1).setData(32, material)

    @staticmethod
    def _num(value, dec=1):
        return "" if value is None else f"{value:.{dec}f}"

    def _add_layer(self):
        material = self.cmb_material.currentData()
        if material is None:
            return
        self._append_row(
            self.table.rowCount() + 1,
            material,
            material.recommended_dft_min,
            material.recommended_dft_min,
            material.recommended_dft_max,
            0,
        )
        self.table.selectRow(self.table.rowCount() - 1)
        self._refresh_compatibility()

    def _delete_layer(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._renumber()
            self._refresh_compatibility()

    def _move_layer(self, direction: int):
        row = self.table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.table.rowCount():
            return
        self.table.blockSignals(True)
        try:
            cells = []
            for col in range(self.table.columnCount()):
                item = self.table.takeItem(row, col)
                cells.append(item)
            self.table.removeRow(row)
            self.table.insertRow(target)
            for col, item in enumerate(cells):
                self.table.setItem(target, col, item)
            self._renumber()
            self.table.selectRow(target)
        finally:
            self.table.blockSignals(False)
        self._refresh_compatibility()

    def _renumber(self, *args):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(row, 0, item)
            item.setText(str(row + 1))
        self.table.blockSignals(False)

    def _materials_from_table(self):
        materials = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            materials.append(item.data(32) if item is not None else None)
        return materials

    def _refresh_compatibility(self, *args):
        materials = self._materials_from_table()
        report = self._compatibility.check_material_sequence(materials)
        self.lbl_compatibility_status.setText(f"Статус: {report.status.value}")
        if not report.transitions:
            self.txt_compatibility.setPlainText(
                "Недостаточно слоёв для проверки. Для проверки соседних переходов нужны минимум два слоя."
            )
            return
        self.txt_compatibility.setPlainText(
            "\n".join(
                f"{index}. {transition.message}"
                for index, transition in enumerate(report.transitions, start=1)
            )
        )

    @staticmethod
    def _float(table, row, col):
        item = table.item(row, col)
        if item is None or not item.text().strip():
            return None
        try:
            return float(item.text().replace(",", "."))
        except ValueError:
            raise ValueError(f"Некорректное число в колонке {col + 1}")

    def _save(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Система", "Укажите название системы")
            return
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Система", "Добавьте хотя бы один слой")
            return

        try:
            with get_session_factory()() as session:
                orm = session.get(CoatingSystemORM, self._current_id) if self._current_id else None
                if orm is None:
                    orm = CoatingSystemORM()
                    session.add(orm)

                orm.system_name = name
                orm.manufacturer = self.ed_manufacturer.text().strip()
                orm.description = self.ed_description.text().strip()
                orm.substrate = self.ed_substrate.text().strip()
                orm.standards = self.ed_standards.text().strip()
                orm.certificate = self.ed_certificate.text().strip()
                orm.number_of_layers = self.table.rowCount()
                orm.is_active = True
                orm.layers.clear()
                session.flush()

                for row in range(self.table.rowCount()):
                    material = self.table.item(row, 1).data(32)
                    if material is None or material.id is None:
                        raise ValueError(f"Материал слоя №{row + 1} не найден")

                    dmin = self._float(self.table, row, 2)
                    target = self._float(self.table, row, 3)
                    dmax = self._float(self.table, row, 4)
                    thinner = self._float(self.table, row, 5) or 0
                    if target is None or target <= 0:
                        raise ValueError(f"Укажите целевой DFT для слоя №{row + 1}")

                    layer_type = self._material_type_value(material)
                    orm.layers.append(
                        CoatingSystemLayerORM(
                            layer_number=row + 1,
                            material_id=material.id,
                            layer_type=layer_type,
                            dft_min=dmin,
                            dft_max=dmax,
                            target_dft=target,
                            thinner_percent=thinner,
                        )
                    )

                session.flush()
                self._current_id = orm.id
                session.commit()

            current_id = self._current_id
            self.reload()
            idx = self.list_systems.findData(current_id)
            if idx >= 0:
                self.list_systems.setCurrentIndex(idx)
            self.systems_changed.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))

    def _delete_system(self):
        if self._current_id is None:
            return
        if QMessageBox.question(
            self,
            "Удаление",
            f"Удалить систему «{self.ed_name.text().strip()}»?",
        ) != QMessageBox.Yes:
            return

        try:
            with get_session_factory()() as session:
                CoatingSystemRepository(session).delete(self._current_id, soft=True)
                session.commit()
            self._current_id = None
            self.reload()
            self.systems_changed.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка удаления", str(exc))
