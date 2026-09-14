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
        self._reviewed_drafts: tuple = ()
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

        reviewed_box = QGroupBox(
            "Reviewed side-by-side DRAFT (явный layout, tds_verified=UNKNOWN)"
        )
        reviewed_layout = QVBoxLayout(reviewed_box)
        self.reviewed_table = QTableWidget(0, 6)
        self.reviewed_table.setHorizontalHeaderLabels([
            "Имя DRAFT", "Лист", "Слои", "DFT known?", "tds_verified", "Источник",
        ])
        self.reviewed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.reviewed_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.reviewed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.reviewed_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        reviewed_layout.addWidget(self.reviewed_table)
        reviewed_actions = QHBoxLayout()
        self.btn_open_reviewed = QPushButton("Открыть reviewed DRAFT в редакторе")
        self.btn_open_reviewed.clicked.connect(self._open_selected_reviewed_draft)
        reviewed_actions.addWidget(self.btn_open_reviewed)
        reviewed_actions.addStretch()
        reviewed_layout.addLayout(reviewed_actions)
        note_reviewed = QLabel(
            "Только листы с reviewed layout. Без auto-CONFIRM и без записи в БД."
        )
        note_reviewed.setWordWrap(True)
        reviewed_layout.addWidget(note_reviewed)
        root.addWidget(reviewed_box, 1)

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
            self._load_reviewed_drafts()
            return
        self._populate_rows()
        self._populate_material_candidates()
        self._load_reviewed_drafts()
        self.details.setPlainText(
            f"Прочитано строк: {len(self._rows)}\n"
            f"Уникальных кандидатов материалов: {len(self._material_candidates)}\n"
            f"Reviewed side-by-side DRAFT: {len(self._reviewed_drafts)}\n\n"
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
                ", ".join(c.name for c in row.material_candidates) or "—",
                (row.source_sha256 or "")[:12],
            ]
            for col, value in enumerate(values):
                self.rows_table.setItem(table_row, col, QTableWidgetItem(str(value)))
        self.rows_table.blockSignals(False)

    def _populate_material_candidates(self) -> None:
        known = {self._norm(m.material_name) for m in self._materials}
        known |= {self._norm(m.display_name()) for m in self._materials}
        self.materials_table.blockSignals(True)
        self.materials_table.setRowCount(0)
        for candidate in self._material_candidates:
            table_row = self.materials_table.rowCount()
            self.materials_table.insertRow(table_row)
            match = "есть в БД" if self._norm(candidate.name) in known else "нет в БД"
            values = [
                candidate.name,
                match,
                f"{candidate.source_path}:{candidate.sheet}:{candidate.row_number}",
                (candidate.source_sha256 or "")[:12],
            ]
            for col, value in enumerate(values):
                self.materials_table.setItem(table_row, col, QTableWidgetItem(str(value)))
        self.materials_table.blockSignals(False)

    @staticmethod
    def _system_text(row: SystemRowCandidate) -> str:
        for key, value in row.values:
            key_norm = key.casefold().replace("ё", "е")
            if any(token in key_norm for token in ("система", "марка", "обозначение", "system")):
                return value or "UNKNOWN"
        return "UNKNOWN"

    def _selected_row(self) -> SystemRowCandidate | None:
        rows = self.rows_table.selectionModel().selectedRows()
        if not rows:
            return None
        index = rows[0].row()
        if index < 0 or index >= len(self._rows):
            return None
        return self._rows[index]

    def _load_reviewed_drafts(self) -> None:
        try:
            self._reviewed_drafts = SystemTemplateService.load_reviewed_side_by_side_drafts(
                self._books_root
            )
        except Exception as exc:
            self._reviewed_drafts = ()
            QMessageBox.warning(
                self,
                "Reviewed DRAFT",
                f"Не удалось загрузить side-by-side DRAFT:\n{exc}",
            )
        self._populate_reviewed_drafts()

    def _populate_reviewed_drafts(self) -> None:
        self.reviewed_table.blockSignals(True)
        self.reviewed_table.setRowCount(0)
        for draft in self._reviewed_drafts:
            row = self.reviewed_table.rowCount()
            self.reviewed_table.insertRow(row)
            dft_known = sum(1 for layer in draft.layers if layer.dft_target is not None)
            values = [
                draft.name,
                draft.source_sheet or "",
                str(len(draft.layers)),
                f"{dft_known}/{len(draft.layers)}",
                draft.metadata.get("tds_verified", "UNKNOWN"),
                Path(draft.source_path).name if draft.source_path else "",
            ]
            for col, value in enumerate(values):
                self.reviewed_table.setItem(row, col, QTableWidgetItem(str(value)))
        self.reviewed_table.blockSignals(False)

    def _selected_reviewed_draft(self):
        rows = self.reviewed_table.selectionModel().selectedRows()
        if not rows:
            return None
        index = rows[0].row()
        if index < 0 or index >= len(self._reviewed_drafts):
            return None
        return self._reviewed_drafts[index]

    def _open_selected_reviewed_draft(self) -> None:
        draft = self._selected_reviewed_draft()
        if draft is None:
            QMessageBox.information(self, "Reviewed DRAFT", "Выберите DRAFT в таблице.")
            return
        try:
            # Unique material bind + TDS evaluate; never auto-CONFIRM.
            prepared = SystemTemplateService.prepare_reviewed_draft_for_review(
                draft, self._materials
            )
            self.editor.load_draft(prepared)
            self.editor.show()
            self.editor.raise_()
        except Exception as exc:
            QMessageBox.warning(
                self, "Reviewed DRAFT", f"Не удалось открыть DRAFT:\n{exc}"
            )

    def _open_selected_draft(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "System Template", "Выберите строку каталога.")
            return
        try:
            draft = SystemTemplateService.build_draft(row, self._materials)
            self.editor.load_draft(draft)
            self.editor.show()
            self.editor.raise_()
        except Exception as exc:
            QMessageBox.warning(self, "System Template", f"Не удалось построить draft:\n{exc}")

    def _create_incomplete_material(self) -> None:
        rows = self.materials_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Material", "Выберите кандидата материала.")
            return
        index = rows[0].row()
        if index < 0 or index >= len(self._material_candidates):
            return
        candidate = self._material_candidates[index]
        name, ok = QInputDialog.getText(
            self, "Неполный Material", "Имя материала:", text=candidate.name
        )
        if not ok or not str(name).strip():
            return
        material = Material(
            material_name=str(name).strip(),
            material_type=MaterialType.UNKNOWN,
            binder_type=BinderType.UNKNOWN,
            notes=(
                f"INCOMPLETE from catalogue {candidate.source_path}/"
                f"{candidate.sheet}:{candidate.row_number}; "
                f"sha256={candidate.source_sha256}"
            ),
        )
        try:
            with get_session_factory()() as session:
                repo = MaterialRepository(session)
                saved = repo.add(material)
                session.commit()
                material_id = saved.id
            QMessageBox.information(
                self, "Material", f"Создана неполная карточка id={material_id}"
            )
            self._materials.append(material)
            self.set_materials(self._materials)
        except Exception as exc:
            QMessageBox.warning(self, "Material", f"Не удалось сохранить:\n{exc}")

    def _persist_confirmed_template(self, draft) -> None:
        try:
            template_id = SystemTemplatePersistenceService().save_confirmed(draft)
            QMessageBox.information(
                self, "System Template", f"Сохранён CONFIRMED template id={template_id}"
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "System Template",
                f"Подтверждённый draft не сохранён:\n{exc}\n\n"
                "Требуются status=CONFIRMED и tds_verified=KNOWN.",
            )

    def _show_row_details(self) -> None:
        row = self._selected_row()
        if row is None:
            self.details.clear()
            return
        lines = [
            f"Источник: {row.source_path}",
            f"Лист: {row.sheet}",
            f"Строка: {row.row_number}",
            f"SHA-256: {row.source_sha256}",
            "",
            "Значения:",
        ]
        for key, value in row.values:
            lines.append(f"  {key}: {value}")
        lines.append("")
        lines.append("Кандидаты материалов:")
        for candidate in row.material_candidates:
            lines.append(f"  - {candidate.name}")
        self.details.setPlainText("\n".join(lines))
