"""UI for the source-traceable Pre-Application Check."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton

from app.domain.models import SystemCalculationResult
from app.domain.pre_application import PreApplicationCheckResult
from app.services.calculation_service import CalculationService


class PreApplicationDialog(QDialog):
    """Read-only presentation of a PreApplicationCheckResult.

    Engineering decisions stay in CalculationService/domain; this dialog only
    renders the current result and allows an explicit re-check of the latest
    calculation inputs.
    """

    def __init__(
        self,
        calculation_service: CalculationService,
        result: SystemCalculationResult,
        parent=None,
    ):
        super().__init__(parent)
        self.calculation_service = calculation_service
        self.calculation_result = result
        self.setWindowTitle("Pre-Application Check")
        self.resize(820, 560)

        layout = QVBoxLayout(self)
        self.status_label = QLabel()
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status_label)

        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report)

        self.recheck_button = QPushButton("Проверить повторно")
        self.recheck_button.clicked.connect(self.refresh)
        layout.addWidget(self.recheck_button)

        self.refresh()

    def _run(self) -> PreApplicationCheckResult:
        result = self.calculation_result
        materials = [layer.material for layer in result.layers]
        dfts = [layer.target_dft for layer in result.layers]
        return self.calculation_service.run_pre_application_check(
            result.object_data,
            materials,
            surface_condition=result.engineering_context.surface_condition,
            actual_dfts=dfts,
            engineering_context=result.engineering_context,
        )

    def refresh(self) -> None:
        check = self._run()
        self.status_label.setText(f"Статус: <b>{check.status}</b>")
        self.report.setPlainText("\n".join(check.summary_lines()))


# Local import kept at module bottom to keep the dialog dependency surface small.
from PySide6.QtCore import Qt
