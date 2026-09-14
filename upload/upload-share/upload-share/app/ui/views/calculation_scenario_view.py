from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.domain.calculation_scenario import CalculationScenario
from app.domain.enums import CompatibilityStatus
from app.domain.engineering_context import EngineeringContext
from app.domain.layer_compatibility import LayerCompatibilityReport
from app.domain.models import CoatingSystem, ObjectData, SystemCalculationResult
from app.services.calculation_scenario_service import CalculationScenarioService


class CalculationScenarioView(QWidget):
    """Scenario UI; arithmetic and compatibility checks remain in services/domain."""
    def __init__(self, service: CalculationScenarioService, parent=None):
        super().__init__(parent)
        self.service = service
        self._systems: list[CoatingSystem] = []
        self._context = EngineeringContext()
        self._results: list[SystemCalculationResult] = []
        self._compatibility: list[LayerCompatibilityReport] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Сценарий расчёта"); title.setProperty("heading", True); root.addWidget(title)
        sub = QLabel("Один объект и несколько альтернативных систем. Все альтернативы рассчитываются существующим CalculationService; складские и закупочные данные не используются.")
        sub.setWordWrap(True); sub.setProperty("subheading", True); root.addWidget(sub)
        box = QGroupBox("Объект сценария"); form = QFormLayout(box)
        self.ed_name = QLineEdit("Сценарий сравнения"); self.ed_object = QLineEdit(); self.ed_customer = QLineEdit(); self.ed_project = QLineEdit()
        self.spin_area = QDoubleSpinBox(); self.spin_area.setRange(.01, 1000000); self.spin_area.setValue(1); self.spin_area.setDecimals(2); self.spin_area.setSuffix(" м²")
        form.addRow("Название:", self.ed_name); form.addRow("Объект:", self.ed_object); form.addRow("Заказчик:", self.ed_customer); form.addRow("Проект:", self.ed_project); form.addRow("Площадь:", self.spin_area); root.addWidget(box)
        sb = QGroupBox("Альтернативы"); sl = QVBoxLayout(sb)
        self.table_systems = QTableWidget(0, 2); self.table_systems.setHorizontalHeaderLabels(["Использовать", "Система"]); self.table_systems.setSelectionMode(QAbstractItemView.NoSelection); self.table_systems.horizontalHeader().setStretchLastSection(True); sl.addWidget(self.table_systems)
        ar = QHBoxLayout(); self.btn_all = QPushButton("Выбрать все"); self.btn_all.clicked.connect(lambda: self._set_all(True)); self.btn_none = QPushButton("Снять все"); self.btn_none.setProperty("secondary", True); self.btn_none.clicked.connect(lambda: self._set_all(False)); self.btn_calc = QPushButton("Рассчитать сценарий"); self.btn_calc.clicked.connect(self._calculate)
        for b in (self.btn_all, self.btn_none, self.btn_calc): ar.addWidget(b)
        ar.addStretch(); sl.addLayout(ar); root.addWidget(sb)
        rb = QGroupBox("Результаты"); rl = QVBoxLayout(rb)
        self.table_result = QTableWidget(0, 1); self.table_result.setHorizontalHeaderLabels(["Показатель"]); self.table_result.setSelectionMode(QAbstractItemView.NoSelection); self.table_result.horizontalHeader().setStretchLastSection(True); rl.addWidget(self.table_result)
        self.btn_cmp = QPushButton("Передать результаты в сравнение"); self.btn_cmp.setEnabled(False); self.btn_cmp.clicked.connect(self._send_to_comparison); rl.addWidget(self.btn_cmp); root.addWidget(rb)

    def set_systems(self, systems: list[CoatingSystem]):
        self._systems = list(systems or []); self.table_systems.setRowCount(len(self._systems))
        for row, s in enumerate(self._systems):
            c = QTableWidgetItem(); c.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable); c.setCheckState(Qt.Unchecked); self.table_systems.setItem(row, 0, c); self.table_systems.setItem(row, 1, QTableWidgetItem(s.system_name or f"Система #{s.id or ''}"))
        self._results = []; self._compatibility = []; self.table_result.setRowCount(0); self.btn_cmp.setEnabled(False)

    def set_engineering_context(self, context: EngineeringContext | None): self._context = context or EngineeringContext()
    def _set_all(self, value):
        state = Qt.Checked if value else Qt.Unchecked
        for r in range(self.table_systems.rowCount()): self.table_systems.item(r, 0).setCheckState(state)
    def _selected(self): return [s for r, s in enumerate(self._systems) if self.table_systems.item(r, 0).checkState() == Qt.Checked]

    def _calculate(self):
        systems = self._selected()
        if not systems: QMessageBox.warning(self, "Сценарий", "Выберите хотя бы одну систему"); return
        try:
            scenario = CalculationScenario(name=self.ed_name.text().strip() or "Сценарий расчёта", object_data=ObjectData(object_name=self.ed_object.text().strip(), customer=self.ed_customer.text().strip(), project=self.ed_project.text().strip(), area_m2=self.spin_area.value()), alternatives=tuple(systems), engineering_context=self._context)
            out = self.service.evaluate(scenario)
        except (ValueError, TypeError) as exc: QMessageBox.warning(self, "Расчёт сценария", str(exc)); return
        self._results = [x.result for x in out.alternatives]; self._compatibility = [x.compatibility for x in out.alternatives]; self._fill(self._results, self._compatibility); self.btn_cmp.setEnabled(bool(self._results))

    @staticmethod
    def _fmt(v):
        if v is None: return "—"
        return f"{v:,.3f}".replace(",", " ") if isinstance(v, float) else str(v)

    @staticmethod
    def _compatibility_text(report: LayerCompatibilityReport) -> str:
        status = report.status
        if status is CompatibilityStatus.ALLOWED: return "ALLOWED"
        if status is CompatibilityStatus.WARNING: return f"WARNING ({len(report.warning_transitions)})"
        if status is CompatibilityStatus.UNKNOWN: return f"UNKNOWN — требуется проверка ({len(report.unknown_transitions)})"
        if status is CompatibilityStatus.FORBIDDEN: return f"FORBIDDEN ({len(report.forbidden_transitions)})"
        return str(status)

    @staticmethod
    def _compatibility_notes(report: LayerCompatibilityReport) -> str:
        if not report.transitions: return "Нет переходов для проверки"
        notes = [transition.message for transition in report.transitions if transition.status is not CompatibilityStatus.ALLOWED]
        return "\n".join(notes) if notes else "Все проверенные переходы разрешены"

    def _fill(self, results: list[SystemCalculationResult], compatibility: list[LayerCompatibilityReport]):
        headers = ["Показатель"] + [r.system.system_name[:40] for r in results]
        rows = [("Количество слоёв", [len(r.layers) for r in results]), ("Общая толщина, мкм", [r.total_dft for r in results]), ("Расход ЛКМ, кг/м²", [r.total_practical_consumption_kg for r in results]), ("Расход ЛКМ, л/м²", [r.total_practical_consumption_l for r in results]), ("Стоимость, руб/м²", [r.total_cost_per_m2 for r in results]), ("Стоимость объекта, руб", [r.total_cost for r in results]), ("Совместимость", [self._compatibility_text(r) for r in compatibility]), ("Примечания совместимости", [self._compatibility_notes(r) for r in compatibility])]
        self.table_result.setColumnCount(len(headers)); self.table_result.setHorizontalHeaderLabels(headers); self.table_result.setRowCount(len(rows))
        for rr, (label, values) in enumerate(rows):
            self.table_result.setItem(rr, 0, QTableWidgetItem(label))
            for cc, v in enumerate(values, 1):
                i = QTableWidgetItem(self._fmt(v)); i.setTextAlignment(Qt.AlignCenter); self.table_result.setItem(rr, cc, i)
        self.table_result.resizeColumnsToContents(); self.table_result.horizontalHeader().setStretchLastSection(True)

    def _send_to_comparison(self):
        parent = self.window(); cmp = getattr(parent, "cmp_view", None)
        if cmp is None or not self._results: QMessageBox.warning(self, "Сравнение", "Экран сравнения недоступен"); return
        cmp.clear()
        for result in self._results: cmp.add_from_calculation(result)
        tabs = getattr(parent, "tabs", None)
        if tabs is not None: tabs.setCurrentWidget(cmp)
        if hasattr(parent, "statusBar"): parent.statusBar().showMessage(f"В сравнение передано систем: {len(self._results)}. Нажмите «Сравнить» для итогового сравнения и экспорта.", 10000)
