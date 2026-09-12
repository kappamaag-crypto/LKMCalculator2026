"""Explicit System Template review editor: materials, DFT, CONFIRM gate."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QDialog, QDialogButtonBox, QLineEdit as QFilterEdit,
)

from app.domain.models import Material
from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.services.system_template_service import SystemTemplateService


class MaterialSelectDialog(QDialog):
    def __init__(self, materials: list[Material], current_id: int | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор материала")
        self._materials = list(materials)
        self._current_id = current_id
        layout = QVBoxLayout(self)
        self.filter = QFilterEdit()
        self.filter.setPlaceholderText("Фильтр…")
        self.filter.textChanged.connect(self._reload)
        layout.addWidget(self.filter)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["id", "Имя", "Производитель", "Статус"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._reload()

    def _reload(self) -> None:
        q = self.filter.text().strip().casefold()
        items = [m for m in self._materials if not q or q in m.display_name().casefold()]
        self.table.setRowCount(0)
        for r, material in enumerate(items):
            self.table.insertRow(r)
            values = [str(material.id or ""), material.display_name(), material.manufacturer or "—",
                      "НЕПОЛНАЯ" if material.is_incomplete else "полная"]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
            if material.id == self._current_id:
                self.table.selectRow(r)

    def selected_material(self) -> Material | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        mid = self.table.item(rows[0].row(), 0).text()
        return next((m for m in self._materials if str(m.id) == mid), None)


class SystemTemplateEditorView(QWidget):
    """Explicit review workflow: edit draft, select materials, then confirm."""
    template_confirmed = Signal(object)

    def __init__(self, materials: list[Material], parent=None):
        super().__init__(parent)
        self._materials = list(materials)
        self._draft: SystemTemplateDraft | None = None
        self._build_ui()

    def set_materials(self, materials: list[Material]) -> None:
        self._materials = list(materials)
        self._reload_material_column()

    def load_draft(self, draft: SystemTemplateDraft) -> None:
        self._draft = draft
        self.name.setText(draft.name)
        self.manufacturer.setText(draft.manufacturer)
        self.description.setPlainText(draft.description)
        self.layers.setRowCount(len(draft.layers))
        for r, layer in enumerate(draft.layers):
            self._set_layer_row(r, layer)
        self._show_provenance(draft)
        self._update_state()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QHBoxLayout()
        form.addWidget(QLabel("Имя:"))
        self.name = QLineEdit()
        form.addWidget(self.name, 2)
        form.addWidget(QLabel("Производитель:"))
        self.manufacturer = QLineEdit()
        form.addWidget(self.manufacturer, 1)
        root.addLayout(form)
        root.addWidget(QLabel("Описание:"))
        self.description = QTextEdit()
        self.description.setMaximumHeight(60)
        root.addWidget(self.description)

        self.layers = QTableWidget(0, 6)
        self.layers.setHorizontalHeaderLabels([
            "№", "Материал", "DFT min", "DFT target", "DFT max", "material_id",
        ])
        self.layers.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.layers.setSelectionMode(QAbstractItemView.SingleSelection)
        self.layers.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        root.addWidget(self.layers, 1)

        actions = QHBoxLayout()
        self.btn_select = QPushButton("Выбрать материал…")
        self.btn_select.clicked.connect(self._select_material)
        actions.addWidget(self.btn_select)
        actions.addStretch()
        root.addLayout(actions)

        self.provenance = QLabel()
        self.provenance.setWordWrap(True)
        root.addWidget(self.provenance)

        self.status = QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_confirm = QPushButton("CONFIRM")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._confirm)
        bottom.addWidget(self.btn_confirm)
        root.addLayout(bottom)

    def _set_layer_row(self, r: int, layer: TemplateLayer) -> None:
        values = [str(layer.layer_number), layer.material_name, self._fmt(layer.dft_min),
                  self._fmt(layer.dft_target), self._fmt(layer.dft_max), str(layer.material_id or "")]
        for c, value in enumerate(values):
            self.layers.setItem(r, c, QTableWidgetItem(value))

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "" if value is None else str(value)

    def _show_provenance(self, draft: SystemTemplateDraft) -> None:
        self.provenance.setText(
            f"Источник: {draft.source_path} / {draft.source_sheet} / row={draft.source_row}\n"
            f"SHA-256: {draft.source_sha256}\n"
            f"TDS verified: {draft.metadata.get('tds_verified', 'UNKNOWN')}"
        )

    def _selected_layer(self) -> int:
        rows = self.layers.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _select_material(self) -> None:
        r = self._selected_layer()
        if r < 0 or self._draft is None:
            QMessageBox.information(self, "System Template", "Выберите слой.")
            return
        current = self._draft.layers[r].material_id
        dlg = MaterialSelectDialog(self._materials, current, self)
        if dlg.exec() != QDialog.Accepted:
            return
        material = dlg.selected_material()
        if material is None:
            return
        layer = self._draft.layers[r]
        layers = list(self._draft.layers)
        layers[r] = TemplateLayer(
            layer_number=layer.layer_number,
            material_name=material.display_name(),
            material_id=material.id,
            dft_min=layer.dft_min,
            dft_target=layer.dft_target,
            dft_max=layer.dft_max,
            source_path=layer.source_path,
            source_sheet=layer.source_sheet,
            source_row=layer.source_row,
            source_sha256=layer.source_sha256,
        )
        self._draft = SystemTemplateDraft(
            name=self.name.text().strip(), manufacturer=self.manufacturer.text().strip(),
            description=self.description.toPlainText().strip(), substrate=self._draft.substrate,
            source_path=self._draft.source_path, source_sheet=self._draft.source_sheet,
            source_row=self._draft.source_row, source_sha256=self._draft.source_sha256,
            layers=tuple(layers), notes=self._draft.notes, status="REVIEW",
            metadata=dict(self._draft.metadata),
        )
        self._set_layer_row(r, layers[r])
        self._update_state()

    def _current_draft(self) -> SystemTemplateDraft | None:
        if self._draft is None:
            return None
        layers = []
        for r, old in enumerate(self._draft.layers):
            def num(col: int) -> float | None:
                text = self.layers.item(r, col).text().strip() if self.layers.item(r, col) else ""
                if not text or text.upper() == "UNKNOWN":
                    return None
                return float(text.replace(",", "."))
            layers.append(TemplateLayer(old.layer_number, old.material_name, old.material_id,
                                        num(2), num(3), num(4), old.source_path, old.source_sheet,
                                        old.source_row, old.source_sha256))
        draft = SystemTemplateDraft(
            name=self.name.text().strip(), manufacturer=self.manufacturer.text().strip(),
            description=self.description.toPlainText().strip(), substrate=self._draft.substrate,
            source_path=self._draft.source_path, source_sheet=self._draft.source_sheet,
            source_row=self._draft.source_row, source_sha256=self._draft.source_sha256,
            layers=tuple(layers), notes=self._draft.notes, status="REVIEW",
            metadata=dict(self._draft.metadata),
        )
        draft = SystemTemplateService.with_tds_verification(draft, self._materials)
        draft.validate()
        return draft

    def _update_state(self) -> None:
        try:
            draft = self._current_draft()
            if draft is None:
                raise ValueError("Нет draft")
            self._draft = SystemTemplateDraft(
                name=draft.name, manufacturer=draft.manufacturer, description=draft.description,
                substrate=draft.substrate, source_path=draft.source_path, source_sheet=draft.source_sheet,
                source_row=draft.source_row, source_sha256=draft.source_sha256, layers=draft.layers,
                notes=draft.notes, status=draft.status, metadata=dict(draft.metadata),
            )
            self._show_provenance(self._draft)
            ok, reasons = SystemTemplateService.can_confirm(draft)
            tds = draft.metadata.get("tds_verified", "UNKNOWN")
            self.status.setText(
                f"TDS={tds}; " + ("ГОТОВ К CONFIRM" if ok else "Review: " + "; ".join(reasons))
            )
            self.btn_confirm.setEnabled(ok)
        except Exception as exc:
            self.status.setText(f"Review: {exc}")
            self.btn_confirm.setEnabled(False)

    def _confirm(self) -> None:
        try:
            draft = self._current_draft()
            if draft is None:
                return
            confirmed = SystemTemplateService.confirm_draft(draft)
            self.template_confirmed.emit(confirmed)
        except Exception as exc:
            QMessageBox.warning(self, "System Template", f"Не удалось подтвердить draft:\n{exc}")

    def _reload_material_column(self) -> None:
        if self._draft is None:
            return
        for r, layer in enumerate(self._draft.layers):
            if r < self.layers.rowCount():
                self.layers.setItem(r, 5, QTableWidgetItem(str(layer.material_id or "")))
