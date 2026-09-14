"""Dialog for the source-traceable Explanation Engine report."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPlainTextEdit, QVBoxLayout, QWidget

from app.domain.explanation import ExplanationReport


class ExplanationDialog(QDialog):
    """Display an ExplanationReport without adding engineering logic to the UI."""

    def __init__(self, report: ExplanationReport, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Пояснение расчёта")
        self.setMinimumSize(760, 520)

        root = QVBoxLayout(self)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText("\n".join(report.summary_lines()))
        root.addWidget(self.text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)
