"""Manual review/editor for catalogue-derived System Template drafts."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QDoubleSpinBox, QComboBox, QFormLayout, QDialog,
    QDialogButtonBox, QGroupBox, QTextEdit,
)

from app.domain.models import Material
from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.services.system_template_service import SystemTemplateService


class MaterialSelectDialog(QDialog):
    def __init__(self, materials: list[Material], current_id: int | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор материала")
        self.setMinimumWidth(620)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по названию, бренду, производителю…")
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Материал", "Производитель", "Статус"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._materials = list(materials)
        self._current_id = current_id
        self.search.textChanged.connect(self._reload)
        self._reload()

    def _reload(self) -> None:
        q = self.search.text().strip().casefold()
        items = [m for m in self._materials if not q or q in m.display_name().casefold()]
        self.table.setRowCount(len(items))
        for r, material in enumerate(items):
            values = [str(material.id or ""), material.display_name(), material.manufacturer or "—",
                      "НЕПОЛНАЯ" if material.is_incomplete else "полная"]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
            if material.id == self._current_id:
                self.table.selectRow(r)

    def selected_material(self) -> Material | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        mid = self.table.item(r, 0).text()
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
        form = QFormLayout()
        self.name = QLineEdit()
        self.manufacturer = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(70)
        form.addRow("Название системы*:", self.name)
        form.addRow("Производитель:", self.manufacturer)
        form.addRow("Описание:", self.description)
        root.addLayout(form)

        box = QGroupBox("Слои")
        box_layout = QVBoxLayout(box)
        self.layers = QTableWidget(0, 6)
        self.layers.setHorizontalHeaderLabels(["№", "Материал", "DFT min, мкм", "DFT target, мкм", "DFT max, мкм", "ID"])
        self.layers.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.layers.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        box_layout.addWidget(self.layers)
        actions = QHBoxLayout()
        self.btn_select = QPushButton("Выбрать материал")
        self.btn_select.clicked.connect(self._select_material)
        actions.addWidget(self.btn_select)
        actions.addStretch()
        box_layout.addLayout(actions)
        root.addWidget(box, 1)

        self.provenance = QTextEdit()
        self.provenance.setReadOnly(True)
        self.provenance.setMaximumHeight(110)
        root.addWidget(QLabel("Provenance / TDS status"))
        root.addWidget(self.provenance)

        bottom = QHBoxLayout()
        self.status = QLabel("Нет draft")
        bottom.addWidget(self.status, 1)
        self.btn_confirm = QPushButton("CONFIRM")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._confirm)
        bottom.addWidget(self.btn_confirm)
        root.addLayout(bottom)

    def _set_layer_row(self, r: int, layer: TemplateLayer) -> None:
        values = [str(layer.layer_number), layer.material_name, self._fmt(layer.dft_min),
                  self._fmt(layer.dft_target), self._fmt(layer.dft_max), str(layer.material_id or "")]
        for c, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~item.flags().__class__(0)) if False else None
            self.layers.setItem(r, c, item)

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "UNKNOWN" if value is None else f"{value:g}"

    def _show_provenance(self, draft: SystemTemplateDraft) -> None:
        self.provenance.setPlainText(
            f"Источник: {draft.source_path}\nЛист: {draft.source_sheet}\n"
            f"Строка: {draft.source_row}\nSHA-256: {draft.source_sha256}\n"
            f"TDS verified: {draft.metadata.get('tds_verified', 'UNKNOWN')}"
        )

    def _selected_layer(self) -> int:
        return self.layers.currentRow()

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
        draft.validate()
        return draft

    def _update_state(self) -> None:
        try:
            draft = self._current_draft()
            if draft is None:
                raise ValueError("Нет draft")
            ok, reasons = SystemTemplateService.can_confirm(draft)
            self.status.setText("ГОТОВ К CONFIRM" if ok else "Review: " + "; ".join(reasons))
            self.btn_confirm.setEnabled(ok)
        except Exception as exc:
            self.status.setText(f"Review: {exc}")
            self.btn_confirm.setEnabled(False)

    def _confirm(self) -> None:
        try:
            draft = self._current_draft()
            if draft is None:
                return
            confirmed = SystemTemplateDraft(
                name=draft.name, manufacturer=draft.manufacturer, description=draft.description,
                substrate=draft.substrate, source_path=draft.source_path, source_sheet=draft.source_sheet,
                source_row=draft.source_row, source_sha256=draft.source_sha256, layers=draft.layers,
                notes=draft.notes, status="CONFIRMED", metadata=dict(draft.metadata),
            )
            confirmed.validate()
            ok, reasons = SystemTemplateService.can_confirm(confirmed)
            if not ok:
                QMessageBox.warning(self, "System Template", "Подтверждение запрещено:\n" + "\n".join(reasons))
                return
            self.template_confirmed.emit(confirmed)
        except Exception as exc:
            QMessageBox.warning(self, "System Template", f"Не удалось подтвердить draft:\n{exc}")
