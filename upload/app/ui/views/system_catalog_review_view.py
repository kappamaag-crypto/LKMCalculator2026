"""Review/staging UI for the tabular ``Системы 1–4`` catalogue.

Spreadsheet rows remain evidence only. Material creation and System Template
confirmation are explicit user actions and never happen implicitly on import.
"""
from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QGroupBox,
    QTextEdit, QInputDialog,
)

from app.domain.models import Material
from app.domain.enums import MaterialType, BinderType
from app.services.system_catalog_importer import (
    discover_system_catalogues,
    unique_material_candidates,
    SystemRowCandidate,
)
from app.services.system_template_service import SystemTemplateService
from app.services.system_template_persistence_service import SystemTemplatePersistenceService
from app.ui.views.system_template_editor_view import SystemTemplateEditorView
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.repositories import MaterialRepository


class SystemCatalogReviewView(QWidget):
    """Review catalogue rows, create incomplete materials explicitly, edit drafts."""

    def __init__(self, books_root: Path, materials: list[Material], parent=None):
        super().__init__(parent)
        self._books_root = Path(books_root)
        self._materials = list(materials)
        self._rows: tuple[SystemRowCandidate, ...] = ()
        self._material_candidates = ()
        self._build_ui()
        self.set_materials(materials)
        self.reload()

    @staticmethod
    def _norm(value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().casefold().replace("ё", "е")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Каталог вариантов систем: Системы 1–4"))
        top.addStretch()
        self.btn_reload = QPushButton("Обновить")
        self.btn_reload.clicked.connect(self.reload)
        top.addWidget(self.btn_reload)
        root.addLayout(top)

        note = QLabel(
            "Review/Staging: Excel не является TDS/нормативом. Автоматических "
            "INSERT/UPDATE нет. Создание неполной карточки, выбор материала и "
            "подтверждение System Template выполняются только отдельными действиями."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        rows_box = QGroupBox("Строки источника")
        rows_layout = QVBoxLayout(rows_box)
        self.rows_table = QTableWidget(0, 6)
        self.rows_table.setHorizontalHeaderLabels([
            "Источник", "Лист", "Строка", "Система / обозначение",
            "Материалы", "SHA-256",
        ])
        self.rows_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rows_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.rows_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.rows_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.rows_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.rows_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.rows_table.itemSelectionChanged.connect(self._show_row_details)
        rows_layout.addWidget(self.rows_table)

        actions = QHBoxLayout()
        self.btn_open_editor = QPushButton("Открыть как System Template")
        self.btn_open_editor.clicked.connect(self._open_selected_draft)
        self.btn_create_material = QPushButton("Создать неполный Material")
        self.btn_create_material.clicked.connect(self._create_incomplete_material)
        actions.addWidget(self.btn_open_editor)
        actions.addWidget(self.btn_create_material)
        actions.addStretch()
        rows_layout.addLayout(actions)
        root.addWidget(rows_box, 1)

        materials_box = QGroupBox("Кандидаты материалов")
        materials_layout = QVBoxLayout(materials_box)
        self.materials_table = QTableWidget(0, 4)
        self.materials_table.setHorizontalHeaderLabels([
            "Кандидат из каталога", "Совпадение с БД", "Источник", "SHA-256",
        ])
        self.materials_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.materials_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.materials_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.materials_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        materials_layout.addWidget(self.materials_table)
        root.addWidget(materials_box, 1)

        details_box = QGroupBox("Детали выбранной строки")
        details_layout = QVBoxLayout(details_box)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(110)
        details_layout.addWidget(self.details)
        root.addWidget(details_box)

        self.editor = SystemTemplateEditorView(self._materials, self)
        self.editor.template_confirmed.connect(self._persist_confirmed_template)

    def set_materials(self, materials: list[Material]) -> None:
        self._materials = list(materials)
        if hasattr(self, "editor"):
            self.editor.set_materials(self._materials)
        if hasattr(self, "rows_table"):
            self._populate_material_candidates()

    def reload(self) -> None:
        try:
            self._rows = discover_system_catalogues(self._books_root)
            self._material_candidates = unique_material_candidates(self._rows)
        except Exception as exc:
            self._rows = ()
            self._material_candidates = ()
            QMessageBox.warning(self, "Каталог систем", f"Не удалось прочитать Системы 1–4: {exc}")
            self._populate_rows()
            self._populate_material_candidates()
            return
        self._populate_rows()
        self._populate_material_candidates()
        self.details.setPlainText(
            f"Прочитано строк: {len(self._rows)}\n"
            f"Уникальных кандидатов материалов: {len(self._material_candidates)}\n\n"
            "Источник не является TDS/нормативным подтверждением применимости. "
            "Перед созданием полноценной системы требуется review и отдельная "
            "проверка TDS/НД."
        )

    def _populate_rows(self) -> None:
        self.rows_table.blockSignals(True)
        self.rows_table.setRowCount(0)
        for row in self._rows:
            table_row = self.rows_table.rowCount()
            self.rows_table.insertRow(table_row)
            values = [
                row.source_path,
                row.sheet,
                str(row.row_number),
                self._system_text(row),
                "; ".join(c.name for c in row.material_candidates) or "—",
                row.source_sha256,
            ]
            for col, value in enumerate(values):
                self.rows_table.setItem(table_row, col, QTableWidgetItem(value))
        self.rows_table.blockSignals(False)
        if self.rows_table.rowCount():
            self.rows_table.selectRow(0)

    def _populate_material_candidates(self) -> None:
        self.materials_table.setRowCount(0)
        material_map: dict[str, list[Material]] = {}
        for material in self._materials:
            material_map.setdefault(self._norm(material.display_name()), []).append(material)
            if material.material_name:
                material_map.setdefault(self._norm(material.material_name), []).append(material)

        for candidate in self._material_candidates:
            row = self.materials_table.rowCount()
            self.materials_table.insertRow(row)
            matches = material_map.get(self._norm(candidate.name), [])
            if not matches:
                status = "НЕ НАЙДЕНО — требует review"
            elif len(matches) == 1:
                status = f"Найден: {matches[0].display_name()} (ID {matches[0].id})"
            else:
                status = "НЕОДНОЗНАЧНО — несколько совпадений"
            values = [
                candidate.name,
                status,
                f"{candidate.source_path} / {candidate.sheet} / строка {candidate.row_number}",
                candidate.source_sha256,
            ]
            for col, value in enumerate(values):
                self.materials_table.setItem(row, col, QTableWidgetItem(value))

    @staticmethod
    def _system_text(row: SystemRowCandidate) -> str:
        pairs = []
        for key, value in row.values:
            key_norm = re.sub(r"[^a-zа-я0-9]+", "", key.casefold().replace("ё", "е"))
            if any(token in key_norm for token in ("система", "марка", "обозначение", "system")):
                pairs.append(f"{key}: {value}")
        return "; ".join(pairs) or "UNKNOWN"

    def _selected_row(self) -> SystemRowCandidate | None:
        index = self.rows_table.currentRow()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def _open_selected_draft(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Каталог систем", "Выберите строку каталога.")
            return
        try:
            draft = SystemTemplateService.build_draft(row, self._materials)
            self.editor.load_draft(draft)
            layout = self.layout()
            if layout.indexOf(self.editor) < 0:
                layout.addWidget(self.editor, 2)
            self.editor.show()
            self.editor.raise_()
        except Exception as exc:
            QMessageBox.warning(self, "System Template", f"Не удалось построить draft:\n{exc}")

    def _create_incomplete_material(self) -> None:
        row = self._selected_row()
        if row is None or not row.material_candidates:
            QMessageBox.information(self, "Material", "Выберите строку с кандидатом материала.")
            return
        names = [c.name for c in row.material_candidates]
        name, ok = QInputDialog.getItem(self, "Неполный Material", "Кандидат:", names, 0, False)
        if not ok or not name.strip():
            return

        matches = [m for m in self._materials if self._norm(m.material_name) == self._norm(name)]
        if matches:
            QMessageBox.information(self, "Material", "Материал с таким названием уже есть в текущей БД.")
            return

        candidate = next(c for c in row.material_candidates if c.name == name)
        provenance = (
            f"Catalogue source: {candidate.source_path}; sheet={candidate.sheet}; "
            f"row={candidate.row_number}; SHA-256={candidate.source_sha256}"
        )
        material = Material(
            manufacturer="",
            brand="",
            material_name=name.strip(),
            material_type=MaterialType.OTHER,
            binder_type=BinderType.UNKNOWN,
            is_incomplete=True,
            notes=f"Создано вручную из staging-кандидата. {provenance}",
        )
        answer = QMessageBox.question(
            self,
            "Подтвердить создание",
            f"Создать неполную карточку Material «{name.strip()}»?\n"
            "Неизвестные технические, коммерческие и TDS-поля останутся пустыми/UNKNOWN.",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            with get_session_factory()() as session:
                saved = MaterialRepository(session).add(material)
                session.commit()
            self._materials.append(saved)
            self.set_materials(self._materials)
            self._populate_rows()
            self._show_row_details()
            QMessageBox.information(self, "Material", f"Неполная карточка создана: ID {saved.id}.")
        except Exception as exc:
            QMessageBox.warning(self, "Material", f"Не удалось создать карточку:\n{exc}")

    def _persist_confirmed_template(self, draft) -> None:
        try:
            template_id = SystemTemplatePersistenceService().save_confirmed(draft)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "System Template",
                f"Подтверждённый draft не сохранён:\n{exc}\n\n"
                "Для persistence требуется подтверждённая TDS applicability (KNOWN).",
            )
            return
        QMessageBox.information(self, "System Template", f"Система сохранена. Template ID: {template_id}")
        self.details.setPlainText(f"System Template сохранён: ID {template_id}")

    def _show_row_details(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        lines = [
            f"Источник: {row.source_path}",
            f"Лист: {row.sheet}",
            f"Строка: {row.row_number}",
            f"SHA-256: {row.source_sha256}",
            "",
            "Поля строки:",
        ]
        lines.extend(f"{key}: {value}" for key, value in row.values)
        lines.append("")
        lines.append("Материалы:")
        lines.extend(f"• {candidate.name}" for candidate in row.material_candidates)
        self.details.setPlainText("\n".join(lines))
