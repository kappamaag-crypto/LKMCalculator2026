"""Вкладка истории расчётов."""

from __future__ import annotations

import json
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QTextEdit, QSplitter,
)
from PySide6.QtCore import Qt, Signal

from app.infrastructure.database.engine import get_session_factory, session_scope, init_db, get_engine
from app.services.history_service import HistoryService
from pathlib import Path
from app.config import DB_PATH


class HistoryView(QWidget):
    """История сохранённых расчётов."""

    load_requested = Signal(dict)  # snapshot dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db_path = DB_PATH
        self._build_ui()
        self.refresh()

    def _get_session_factory(self):
        # Use /tmp if sandbox has I/O issues with project data dir
        path = self._db_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            engine = get_engine(path)
            init_db(engine)
            return get_session_factory(engine)
        except Exception:
            path = Path("/tmp/lkm_calculator.sqlite")
            engine = get_engine(path)
            init_db(engine)
            return get_session_factory(engine)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLabel("История расчётов")
        title.setProperty("heading", True)
        root.addWidget(title)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("Обновить")
        btn_refresh.setProperty("secondary", True)
        btn_refresh.clicked.connect(self.refresh)
        btn_delete = QPushButton("Удалить")
        btn_delete.setProperty("secondary", True)
        btn_delete.clicked.connect(self._on_delete)
        btn_load = QPushButton("Открыть снимок")
        btn_load.clicked.connect(self._on_load)
        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_load)
        btn_row.addStretch()
        root.addLayout(btn_row)

        splitter = QSplitter(Qt.Vertical)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата", "№", "Объект", "Система", "DFT, мкм", "Стоимость, руб"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self.table)

        self.txt_detail = QTextEdit()
        self.txt_detail.setReadOnly(True)
        self.txt_detail.setMaximumHeight(200)
        splitter.addWidget(self.txt_detail)

        root.addWidget(splitter)

    def refresh(self) -> None:
        self.table.setRowCount(0)
        self.txt_detail.clear()
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                svc = HistoryService(session)
                rows = svc.list_calculations(limit=200)
                self.table.setRowCount(len(rows))
                for r, calc in enumerate(rows):
                    date_str = calc.created_at.strftime("%d.%m.%Y %H:%M") if calc.created_at else "—"
                    values = [
                        str(calc.id),
                        date_str,
                        calc.calculation_number or "—",
                        calc.object_name or "—",
                        calc.system_name or "—",
                        f"{calc.total_dft:.0f}",
                        f"{calc.total_cost:,.0f}".replace(",", " "),
                    ]
                    for c, v in enumerate(values):
                        item = QTableWidgetItem(v)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        if c == 0:
                            item.setData(Qt.UserRole, calc.id)
                        self.table.setItem(r, c, item)
        except Exception as e:
            self.txt_detail.setPlainText(f"Ошибка загрузки истории: {e}")

    def _selected_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _on_select(self) -> None:
        calc_id = self._selected_id()
        if calc_id is None:
            return
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                svc = HistoryService(session)
                calc = svc.get_calculation(calc_id)
                if not calc:
                    return
                lines = [
                    f"ID: {calc.id}",
                    f"Дата: {calc.created_at}",
                    f"№: {calc.calculation_number}",
                    f"Объект: {calc.object_name}",
                    f"Заказчик: {calc.customer}",
                    f"Система: {calc.system_name}",
                    f"Площадь: {calc.area_m2} м²",
                    f"DFT: {calc.total_dft} мкм",
                    f"Расход: {calc.total_consumption_kg} кг/м²",
                    f"Стоимость: {calc.total_cost_per_m2} руб/м²",
                    f"Стоимость объекта: {calc.total_cost} руб",
                    "",
                    "Слои:",
                ]
                for layer in calc.layers:
                    lines.append(
                        f"  {layer.layer_number}. {layer.material_name}: "
                        f"DFT={layer.dry_thickness} мкм, "
                        f"{layer.consumption_kg} кг/м², "
                        f"{layer.cost_per_m2} руб/м²"
                    )
                if calc.notes:
                    lines.append(f"\nЗаметки: {calc.notes}")
                self.txt_detail.setPlainText("\n".join(lines))
        except Exception as e:
            self.txt_detail.setPlainText(str(e))

    def _on_delete(self) -> None:
        calc_id = self._selected_id()
        if calc_id is None:
            QMessageBox.information(self, "История", "Выберите запись")
            return
        reply = QMessageBox.question(
            self, "Удаление",
            f"Удалить расчёт ID={calc_id}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                HistoryService(session).delete_calculation(calc_id)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_load(self) -> None:
        calc_id = self._selected_id()
        if calc_id is None:
            QMessageBox.information(self, "История", "Выберите запись")
            return
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                calc = HistoryService(session).get_calculation(calc_id)
                if not calc or not calc.snapshot_json:
                    QMessageBox.warning(self, "История", "Снимок отсутствует")
                    return
                snapshot = json.loads(calc.snapshot_json)
                self.load_requested.emit(snapshot)
                QMessageBox.information(
                    self, "История",
                    "Снимок загружен.\nПерейдите на вкладку «Расчёт» для просмотра данных."
                )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def save_result(self, result) -> None:
        """Сохранить SystemCalculationResult в историю."""
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                calc_id = HistoryService(session).save_calculation(result)
            self.refresh()
            return calc_id
        except Exception as e:
            QMessageBox.warning(self, "История", f"Не удалось сохранить: {e}")
            return None
