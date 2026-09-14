"""Информационный экран 2К-материалов без закупочной логики."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLabel, QComboBox

from app.infrastructure.database.engine import init_db, get_session_factory
from app.infrastructure.database.models import MaterialORM
from app.services.two_component_service import TwoComponentService


class TwoComponentView(QWidget):
    """Показывает только справочные сведения о компонентах 2К-материала."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._materials: list[tuple[int, str]] = []
        self._build_ui()
        self._load_materials()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel("2К-материалы — справочная информация")
        title.setProperty("heading", True)
        root.addWidget(title)

        self.cmb_material = QComboBox()
        self.cmb_material.currentIndexChanged.connect(self._show_selected)
        root.addWidget(self.cmb_material)

        box = QGroupBox("Информация о смешении")
        form = QFormLayout(box)
        self.lbl_a = QLabel("—")
        self.lbl_b = QLabel("—")
        self.lbl_ratio = QLabel("—")
        self.lbl_pot = QLabel("—")
        self.lbl_induction = QLabel("—")
        self.lbl_notes = QLabel("—")
        self.lbl_notes.setWordWrap(True)
        form.addRow("Компонент A:", self.lbl_a)
        form.addRow("Компонент B:", self.lbl_b)
        form.addRow("Соотношение A:B:", self.lbl_ratio)
        form.addRow("Рабочее время (pot life):", self.lbl_pot)
        form.addRow("Индукционная выдержка:", self.lbl_induction)
        form.addRow("Примечания / источник:", self.lbl_notes)
        root.addWidget(box)

        note = QLabel("Справочная информация. Расход, закупка, фасовка, комплекты и остатки для 2К-материалов не рассчитываются.")
        note.setWordWrap(True)
        note.setProperty("subheading", True)
        root.addWidget(note)
        root.addStretch()

    def _load_materials(self) -> None:
        try:
            init_db()
            session_factory = get_session_factory()
            with session_factory() as session:
                rows = session.query(MaterialORM).filter(
                    MaterialORM.is_two_component.is_(True),
                    MaterialORM.is_active.is_(True),
                ).order_by(MaterialORM.material_name).all()
                self._materials = [(row.id, row.material_name) for row in rows]
        except Exception as exc:
            self.cmb_material.addItem("Ошибка загрузки 2К-справочника")
            self.cmb_material.setEnabled(False)
            self.lbl_notes.setText(str(exc))
            return

        self.cmb_material.clear()
        if not self._materials:
            self.cmb_material.addItem("Нет материалов с подтверждёнными 2К-данными")
            self.cmb_material.setEnabled(False)
            return
        self.cmb_material.setEnabled(True)
        for material_id, name in self._materials:
            self.cmb_material.addItem(name, material_id)
        self._show_selected()

    @staticmethod
    def _fmt_minutes(value) -> str:
        return f"{value:g} мин" if value is not None else "не указано"

    def _show_selected(self) -> None:
        material_id = self.cmb_material.currentData()
        if material_id is None:
            return
        try:
            session_factory = get_session_factory()
            with session_factory() as session:
                result = TwoComponentService.describe_from_database(session, int(material_id))
        except Exception as exc:
            self.lbl_notes.setText(f"Ошибка чтения данных: {exc}")
            return

        if result is None:
            self.lbl_a.setText("не указано")
            self.lbl_b.setText("не указано")
            self.lbl_ratio.setText("не указано")
            self.lbl_pot.setText("не указано")
            self.lbl_induction.setText("не указано")
            self.lbl_notes.setText("Для материала нет подтверждённой записи смешения.")
            return

        self.lbl_a.setText(result.component_a.name if result.component_a else "не указано")
        self.lbl_b.setText(result.component_b.name if result.component_b else "не указано")
        self.lbl_ratio.setText(result.ratio_text)
        self.lbl_pot.setText(self._fmt_minutes(result.working_time_minutes))
        self.lbl_induction.setText(self._fmt_minutes(result.induction_time_minutes))
        self.lbl_notes.setText(result.notes or "Источник не указан")
