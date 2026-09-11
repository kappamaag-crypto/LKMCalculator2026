"""Review/staging UI for the tabular ``Системы 1–4`` catalogue.

The view is deliberately review-first: spreadsheet rows are never written to the
material/system database. Spreadsheet data is catalogue evidence only, not TDS.
"""
from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QGroupBox,
    QTextEdit,
)

from app.domain.models import Material
from app.services.system_catalog_importer import (
    discover_system_catalogues,
    unique_material_candidates,
    SystemRowCandidate,
)


class SystemCatalogReviewView(QWidget):
    """Read-only staging/review of system catalogue rows and material matches."""

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
            "Режим Review/Staging: данные Excel только сопоставляются с БД. "
            "Автоматического сохранения материалов или систем нет. Значения, "
            "которых нет в источнике, не заполняются и остаются UNKNOWN."
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

    def set_materials(self, materials: list[Material]) -> None:
        self._materials = list(materials)
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
            system_text = self._system_text(row)
            materials_text = "; ".join(c.name for c in row.material_candidates) or "—"
            values = [
                row.source_path,
                row.sheet,
                str(row.row_number),
                system_text,
                materials_text,
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

    def _show_row_details(self) -> None:
        index = self.rows_table.currentRow()
        if index < 0 or index >= len(self._rows):
            return
        row = self._rows[index]
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
