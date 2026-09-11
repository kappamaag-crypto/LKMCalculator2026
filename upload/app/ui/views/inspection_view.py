"""Inspection workflow UI."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget
from app.domain.inspection import InspectionRecord
from app.services.inspection_service import InspectionService

class InspectionView(QWidget):
    record_created = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = InspectionService()
        form_box = QGroupBox("Инспекция / контроль качества")
        form = QFormLayout(form_box)
        self.inspection_id = QLineEdit()
        self.object_name = QLineEdit()
        self.inspector = QLineEdit()
        self.standard = QLineEdit()
        self.source = QLineEdit()
        self.system = QLineEdit()
        self.status = QLineEdit("UNKNOWN")
        for label, widget in (("№", self.inspection_id), ("Объект", self.object_name), ("Инспектор", self.inspector), ("НД", self.standard), ("Источник", self.source), ("Система", self.system), ("Статус", self.status)):
            form.addRow(label, widget)
        self.notes = QPlainTextEdit()
        self.create = QPushButton("Создать запись")
        self.create.clicked.connect(self._create)
        root = QVBoxLayout(self)
        root.addWidget(form_box)
        root.addWidget(self.notes)
        root.addWidget(self.create)
        self.summary = QPlainTextEdit(); self.summary.setReadOnly(True); root.addWidget(self.summary)

    def _create(self):
        record = self.service.create_record(self.inspection_id.text(), object_name=self.object_name.text(), inspector=self.inspector.text(), standard_reference=self.standard.text(), standard_source=self.source.text(), coating_system=self.system.text(), notes=self.notes.toPlainText(), acceptance_status=self.status.text().strip() or "UNKNOWN")
        self.summary.setPlainText(self.service.summary(record))
        self.record_created.emit(record)
