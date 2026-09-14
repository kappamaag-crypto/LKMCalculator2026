"""Вкладка базы материалов: инженерная карточка материала + CRUD."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.domain.enums import ApplicationMethod, BinderType, MaterialType
from app.domain.models import Material
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.repositories import MaterialRepository


class _NullableDouble:
    """QDoubleSpinBox + explicit presence flag; zero is a real entered value."""

    def __init__(self, value: Optional[float], minimum: float, maximum: float, decimals: int = 2):
        self.enabled = QCheckBox("задано")
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setDecimals(decimals)
        self.spin.setValue(value if value is not None else 0.0)
        self.enabled.setChecked(value is not None)
        self.spin.setEnabled(value is not None)
        self.enabled.toggled.connect(self.spin.setEnabled)

    def widget(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.enabled)
        layout.addWidget(self.spin)
        return row

    def value(self) -> Optional[float]:
        return self.spin.value() if self.enabled.isChecked() else None


class MaterialEditDialog(QDialog):
    """Полная инженерная карточка Material без скрытых значений и TDS URL."""

    def __init__(self, material: Optional[Material] = None, parent=None):
        super().__init__(parent)
        self.material = material
        self.setWindowTitle("Материал" if material else "Новый материал")
        self.setMinimumSize(760, 760)

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        root = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.ed_name = QLineEdit(material.material_name if material else "")
        self.ed_manufacturer = QLineEdit(material.manufacturer if material else "")
        self.ed_brand = QLineEdit(material.brand if material else "")
        self.ed_description = QTextEdit(material.description if material else "")
        self.ed_description.setMaximumHeight(80)
        self.ed_color = QLineEdit(material.color if material else "")
        self.ed_ral = QLineEdit(material.ral if material else "")

        self.cmb_type = QComboBox()
        for value in MaterialType:
            self.cmb_type.addItem(value.value, value)
        self._set_combo(self.cmb_type, material.material_type if material else MaterialType.OTHER)

        self.cmb_binder = QComboBox()
        for value in BinderType:
            self.cmb_binder.addItem(value.value, value)
        self._set_combo(self.cmb_binder, material.binder_type if material else BinderType.UNKNOWN)

        self.cmb_application_method = QComboBox()
        self.cmb_application_method.addItem("не задано", None)
        for value in ApplicationMethod:
            self.cmb_application_method.addItem(value.value, value)
        self._set_combo(self.cmb_application_method, material.application_method if material else None)

        def val(name: str) -> Optional[float]:
            return getattr(material, name, None) if material else None

        self.spin_density = _NullableDouble(val("density"), 0, 10, 3)
        self.spin_solids = _NullableDouble(val("solids_percent"), 0, 100, 2)
        self.spin_solids_volume = _NullableDouble(val("solids_by_volume_percent"), 0, 100, 2)
        self.spin_voc = _NullableDouble(val("voc"), 0, 1000, 2)
        self.spin_theoretical_coverage = _NullableDouble(val("theoretical_coverage"), 0, 1000, 3)
        self.spin_price_kg = _NullableDouble(val("price_per_kg"), 0, 1000000, 2)
        self.spin_price_liter = _NullableDouble(val("price_per_liter"), 0, 1000000, 2)
        self.spin_min_application_temperature = _NullableDouble(val("min_application_temperature"), -100, 100, 1)
        self.spin_max_application_temperature = _NullableDouble(val("max_application_temperature"), -100, 200, 1)
        self.spin_min_recoat_time_h = _NullableDouble(val("min_recoat_time_h"), 0, 10000, 2)
        self.spin_max_recoat_time_h = _NullableDouble(val("max_recoat_time_h"), 0, 10000, 2)
        self.spin_drying_time_h = _NullableDouble(val("drying_time_h"), 0, 10000, 2)
        self.spin_full_cure_time_h = _NullableDouble(val("full_cure_time_h"), 0, 10000, 2)
        self.spin_pot_life_h = _NullableDouble(val("pot_life_h"), 0, 1000, 2)
        self.spin_induction_time_min = _NullableDouble(val("induction_time_min"), 0, 1000, 2)
        self.spin_max_relative_humidity = _NullableDouble(val("max_relative_humidity"), 0, 100, 1)
        self.spin_min_dew_point_margin_c = _NullableDouble(val("min_dew_point_margin_c"), -20, 100, 1)
        self.spin_dft_min = _NullableDouble(val("recommended_dft_min"), 0, 5000, 1)
        self.spin_dft_max = _NullableDouble(val("recommended_dft_max"), 0, 5000, 1)
        self.spin_max_single_layer_dft = _NullableDouble(val("max_single_layer_dft"), 0, 5000, 1)
        self.spin_thinner_min = _NullableDouble(val("thinner_percent_min"), 0, 100, 2)
        self.spin_thinner_max = _NullableDouble(val("thinner_percent_max"), 0, 100, 2)
        self.spin_packaging_kg = _NullableDouble(val("packaging_kg"), 0, 10000, 2)
        self.spin_packaging_l = _NullableDouble(val("packaging_l"), 0, 10000, 2)

        self.chk_vat = QCheckBox("Цена включает НДС")
        self.chk_vat.setChecked(material.prices_include_vat if material else True)
        self.chk_two_component = QCheckBox("Двухкомпонентный материал")
        self.chk_two_component.setChecked(material.is_two_component if material else False)
        self.chk_thinner_required = QCheckBox("Разбавитель требуется")
        self.chk_thinner_required.setChecked(material.thinner_required if material else False)
        self.chk_active = QCheckBox("Активен")
        self.chk_active.setChecked(material.is_active if material else True)
        self.chk_incomplete = QCheckBox("Карточка неполная")
        self.chk_incomplete.setChecked(material.is_incomplete if material else False)

        self.ed_thinner_name = QLineEdit(material.thinner_name if material else "")
        self.cmb_thinner_basis = QComboBox()
        self.cmb_thinner_basis.addItem("BY_PAINT_VOLUME", "BY_PAINT_VOLUME")
        self.cmb_thinner_basis.addItem("BY_TOTAL_MIX", "BY_TOTAL_MIX")
        self._set_combo_data(self.cmb_thinner_basis, material.thinner_basis if material else "BY_PAINT_VOLUME")

        self.ed_packaging_kg = self.spin_packaging_kg
        self.ed_packaging_l = self.spin_packaging_l
        self.ed_datasheet = QLineEdit(material.datasheet if material else "")
        self.ed_datasheet_version = QLineEdit(material.datasheet_version if material else "")
        self.ed_datasheet_date = QLineEdit(material.datasheet_date or "" if material else "")
        self.ed_sds = QLineEdit(material.safety_data_sheet if material else "")
        self.ed_certificate = QLineEdit(material.certificate if material else "")
        self.ed_certificate_version = QLineEdit(material.certificate_version if material else "")
        self.ed_test_protocol = QLineEdit(material.test_protocol if material else "")
        self.ed_notes = QTextEdit(material.notes if material else "")
        self.ed_notes.setMaximumHeight(100)

        self._add_group(root, "Идентификация", [
            ("Название*:", self.ed_name), ("Производитель:", self.ed_manufacturer),
            ("Бренд:", self.ed_brand), ("Тип:", self.cmb_type),
            ("Связующее:", self.cmb_binder), ("Способ нанесения:", self.cmb_application_method),
            ("Описание:", self.ed_description), ("Цвет:", self.ed_color), ("RAL:", self.ed_ral),
        ])
        self._add_group(root, "Физические и финансовые параметры", [
            ("Плотность, кг/л:", self.spin_density.widget()),
            ("Сухой остаток, %:", self.spin_solids.widget()),
            ("Сухой остаток по объёму, %:", self.spin_solids_volume.widget()),
            ("VOC:", self.spin_voc.widget()),
            ("Теоретическая укрывистость, м²/л:", self.spin_theoretical_coverage.widget()),
            ("Цена, руб/кг:", self.spin_price_kg.widget()),
            ("Цена, руб/л:", self.spin_price_liter.widget()),
            ("НДС:", self.chk_vat),
        ])
        self._add_group(root, "Нанесение и отверждение", [
            ("Температура нанесения min, °C:", self.spin_min_application_temperature.widget()),
            ("Температура нанесения max, °C:", self.spin_max_application_temperature.widget()),
            ("Перекрытие min, ч:", self.spin_min_recoat_time_h.widget()),
            ("Перекрытие max, ч:", self.spin_max_recoat_time_h.widget()),
            ("Время высыхания, ч:", self.spin_drying_time_h.widget()),
            ("Полное отверждение, ч:", self.spin_full_cure_time_h.widget()),
            ("Жизнеспособность, ч:", self.spin_pot_life_h.widget()),
            ("Индукция, мин:", self.spin_induction_time_min.widget()),
            ("Макс. относительная влажность, %:", self.spin_max_relative_humidity.widget()),
            ("Мин. запас до точки росы, °C:", self.spin_min_dew_point_margin_c.widget()),
        ])
        self._add_group(root, "DFT", [
            ("Рекомендуемый DFT min, мкм:", self.spin_dft_min.widget()),
            ("Рекомендуемый DFT max, мкм:", self.spin_dft_max.widget()),
            ("Макс. DFT одного слоя, мкм:", self.spin_max_single_layer_dft.widget()),
        ])
        self._add_group(root, "Разбавитель", [
            ("Требуется:", self.chk_thinner_required), ("Наименование:", self.ed_thinner_name),
            ("Расход min, %:", self.spin_thinner_min.widget()), ("Расход max, %:", self.spin_thinner_max.widget()),
            ("База процента:", self.cmb_thinner_basis),
        ])
        self._add_group(root, "Комплектация", [
            ("Упаковка, кг:", self.spin_packaging_kg.widget()), ("Упаковка, л:", self.spin_packaging_l.widget()),
            ("2К:", self.chk_two_component),
        ])
        self._add_group(root, "Документы и примечания", [
            ("TDS / обозначение:", self.ed_datasheet), ("Версия TDS:", self.ed_datasheet_version),
            ("Дата TDS:", self.ed_datasheet_date), ("SDS / обозначение:", self.ed_sds),
            ("Сертификат:", self.ed_certificate), ("Версия сертификата:", self.ed_certificate_version),
            ("Протокол испытаний:", self.ed_test_protocol), ("Примечания:", self.ed_notes),
            ("Статус:", self._status_widget()),
        ])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    @staticmethod
    def _set_combo(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _status_widget(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chk_active)
        layout.addWidget(self.chk_incomplete)
        layout.addStretch()
        return row

    @staticmethod
    def _add_group(root: QVBoxLayout, title: str, rows: list[tuple[str, QWidget]]) -> None:
        group = QGroupBox(title)
        form = QFormLayout(group)
        for label, widget in rows:
            form.addRow(label, widget)
        root.addWidget(group)

    def get_material(self) -> Material:
        base = self.material or Material()
        return Material(
            id=base.id,
            manufacturer=self.ed_manufacturer.text().strip(), brand=self.ed_brand.text().strip(),
            material_name=self.ed_name.text().strip(),
            material_type=self.cmb_type.currentData() or MaterialType.OTHER,
            binder_type=self.cmb_binder.currentData() or BinderType.UNKNOWN,
            description=self.ed_description.toPlainText().strip(),
            density=self.spin_density.value(), solids_percent=self.spin_solids.value(),
            solids_by_volume_percent=self.spin_solids_volume.value(), voc=self.spin_voc.value(),
            color=self.ed_color.text().strip(), ral=self.ed_ral.text().strip(),
            price_per_kg=self.spin_price_kg.value(), price_per_liter=self.spin_price_liter.value(),
            prices_include_vat=self.chk_vat.isChecked(),
            theoretical_coverage=self.spin_theoretical_coverage.value(),
            application_method=self.cmb_application_method.currentData(),
            min_application_temperature=self.spin_min_application_temperature.value(),
            max_application_temperature=self.spin_max_application_temperature.value(),
            min_recoat_time_h=self.spin_min_recoat_time_h.value(),
            max_recoat_time_h=self.spin_max_recoat_time_h.value(),
            drying_time_h=self.spin_drying_time_h.value(), full_cure_time_h=self.spin_full_cure_time_h.value(),
            pot_life_h=self.spin_pot_life_h.value(), induction_time_min=self.spin_induction_time_min.value(),
            max_relative_humidity=self.spin_max_relative_humidity.value(),
            min_dew_point_margin_c=self.spin_min_dew_point_margin_c.value(),
            recommended_dft_min=self.spin_dft_min.value(), recommended_dft_max=self.spin_dft_max.value(),
            max_single_layer_dft=self.spin_max_single_layer_dft.value(),
            thinner_required=self.chk_thinner_required.isChecked(), thinner_name=self.ed_thinner_name.text().strip(),
            thinner_percent_min=self.spin_thinner_min.value(), thinner_percent_max=self.spin_thinner_max.value(),
            thinner_basis=self.cmb_thinner_basis.currentData() or "BY_PAINT_VOLUME",
            packaging_kg=self.spin_packaging_kg.value(), packaging_l=self.spin_packaging_l.value(),
            is_two_component=self.chk_two_component.isChecked(),
            datasheet=self.ed_datasheet.text().strip(), datasheet_version=self.ed_datasheet_version.text().strip(),
            datasheet_date=self.ed_datasheet_date.text().strip() or None,
            safety_data_sheet=self.ed_sds.text().strip(), certificate=self.ed_certificate.text().strip(),
            certificate_version=self.ed_certificate_version.text().strip(), test_protocol=self.ed_test_protocol.text().strip(),
            is_active=self.chk_active.isChecked(), is_incomplete=self.chk_incomplete.isChecked(),
            notes=self.ed_notes.toPlainText().strip(), created_at=base.created_at, updated_at=base.updated_at,
        )


class MaterialsView(QWidget):
    """База ЛКМ — просмотр и редактирование с сохранением в SQLite."""

    materials_changed = Signal(list)

    def __init__(self, materials: list[Material] | None = None, parent=None):
        super().__init__(parent)
        self._materials = list(materials or [])
        self._next_id = max((m.id or 0 for m in self._materials), default=0) + 1
        self._build_ui()
        self._reload_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        title = QLabel("База материалов")
        title.setProperty("heading", True)
        root.addWidget(title)
        sr = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("Поиск: название, производитель, связующее…")
        self.ed_search.textChanged.connect(self._reload_table)
        sr.addWidget(self.ed_search)
        root.addLayout(sr)
        br = QHBoxLayout()
        a = QPushButton("Добавить")
        a.clicked.connect(self._on_add)
        e = QPushButton("Изменить")
        e.setProperty("secondary", True)
        e.clicked.connect(self._on_edit)
        d = QPushButton("Удалить")
        d.setProperty("secondary", True)
        d.clicked.connect(self._on_delete)
        br.addWidget(a); br.addWidget(e); br.addWidget(d); br.addStretch(); root.addLayout(br)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Название", "Производитель", "Тип", "Связующее", "Плотность",
            "СО, %", "СО по объёму, %", "Цена, руб/кг", "Цена, руб/л",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(1, self.table.horizontalHeader().Stretch)
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

    def _filtered(self):
        q = self.ed_search.text().strip().lower()
        return self._materials if not q else [
            m for m in self._materials if q in f"{m.material_name} {m.manufacturer} {m.brand} {m.binder_type}".lower()
        ]

    def _reload_table(self):
        rows = self._filtered()
        self.table.setRowCount(len(rows))
        for r, m in enumerate(rows):
            vals = [
                str(m.id or ""), m.material_name, m.manufacturer or "—",
                m.material_type.value if hasattr(m.material_type, "value") else str(m.material_type),
                m.binder_type.value if hasattr(m.binder_type, "value") else str(m.binder_type),
                f"{m.density:.2f}" if m.density is not None else "—",
                f"{m.solids_percent:.0f}" if m.solids_percent is not None else "—",
                f"{m.solids_by_volume_percent:.0f}" if m.solids_by_volume_percent is not None else "—",
                f"{m.price_per_kg:.0f}" if m.price_per_kg is not None else "—",
                f"{m.price_per_liter:.0f}" if m.price_per_liter is not None else "—",
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 0:
                    item.setData(Qt.UserRole, m.id)
                self.table.setItem(r, c, item)
        self.lbl_count.setText(f"Материалов: {len(rows)} (всего {len(self._materials)})")

    def _selected_material(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        mid = item.data(Qt.UserRole) if item else None
        return next((m for m in self._materials if m.id == mid), None)

    @staticmethod
    def _save_if_missing(material):
        with get_session_factory()() as session:
            repo = MaterialRepository(session)
            existing = repo.get_by_name(material.material_name)
            if existing is not None:
                return existing
            saved = repo.add(material)
            session.commit()
            return saved

    def _on_add(self):
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
        idx = next((i for i, m in enumerate(self._materials) if m.material_name.casefold() == saved.material_name.casefold()), None)
        if idx is None:
            self._materials.append(saved)
        else:
            self._materials[idx] = saved
        self._next_id = max(self._next_id, (saved.id or 0) + 1)
        self._reload_table()
        self.materials_changed.emit(self.get_materials())

    def _on_edit(self):
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

    def _on_delete(self):
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
