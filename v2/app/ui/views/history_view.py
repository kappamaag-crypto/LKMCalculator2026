"""Вкладка истории расчётов."""

from __future__ import annotations

import json
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QTextEdit, QSplitter,
)
from PySide6.QtCore import Qt, Signal

from app.infrastructure.database.engine import get_session_factory, session_scope, init_db, get_engine
from app.services.history_service import HistoryService
from app.config import DB_PATH


class HistoryView(QWidget):
    load_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db_path = DB_PATH
        self._build_ui()
        self.refresh()

    def _get_session_factory(self):
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
        title = QLabel("\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u0440\u0430\u0441\u0447\u0451\u0442\u043e\u0432")
        title.setProperty("heading", True)
        root.addWidget(title)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c")
        btn_refresh.setProperty("secondary", True)
        btn_refresh.clicked.connect(self.refresh)
        btn_delete = QPushButton("\u0423\u0434\u0430\u043b\u0438\u0442\u044c")
        btn_delete.setProperty("secondary", True)
        btn_delete.clicked.connect(self._on_delete)
        btn_load = QPushButton("\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u0441\u043d\u0438\u043c\u043e\u043a")
        btn_load.clicked.connect(self._on_load)
        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_load)
        btn_row.addStretch()
        root.addLayout(btn_row)

        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID", "\u0414\u0430\u0442\u0430", "\u2116", "\u041e\u0431\u044a\u0435\u043a\u0442", "\u0421\u0438\u0441\u0442\u0435\u043c\u0430", "DFT, \u043c\u043a\u043c", "\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c, \u0440\u0443\u0431"
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
                    date_str = calc.created_at.strftime("%d.%m.%Y %H:%M") if calc.created_at else "\u2014"
                    values = [
                        str(calc.id), date_str,
                        calc.calculation_number or "\u2014",
                        calc.object_name or "\u2014",
                        calc.system_name or "\u2014",
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
            self.txt_detail.setPlainText(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438 \u0438\u0441\u0442\u043e\u0440\u0438\u0438: {e}")

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
                calc = HistoryService(session).get_calculation(calc_id)
                if not calc:
                    return
                lines = [
                    f"ID: {calc.id}", f"\u0414\u0430\u0442\u0430: {calc.created_at}",
                    f"\u2116: {calc.calculation_number}", f"\u041e\u0431\u044a\u0435\u043a\u0442: {calc.object_name}",
                    f"\u0417\u0430\u043a\u0430\u0437\u0447\u0438\u043a: {calc.customer}", f"\u0421\u0438\u0441\u0442\u0435\u043c\u0430: {calc.system_name}",
                    f"\u041f\u043b\u043e\u0449\u0430\u0434\u044c: {calc.area_m2} \u043c\u00b2", f"DFT: {calc.total_dft} \u043c\u043a\u043c",
                    f"\u0420\u0430\u0441\u0445\u043e\u0434: {calc.total_consumption_kg} \u043a\u0433/\u043c\u00b2",
                    f"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c: {calc.total_cost_per_m2} \u0440\u0443\u0431/\u043c\u00b2",
                    f"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u043e\u0431\u044a\u0435\u043a\u0442\u0430: {calc.total_cost} \u0440\u0443\u0431", "", "\u0421\u043b\u043e\u0438:",
                ]
                for layer in calc.layers:
                    lines.append(
                        f"  {layer.layer_number}. {layer.material_name}: "
                        f"DFT={layer.dry_thickness} \u043c\u043a\u043c, {layer.consumption_kg} \u043a\u0433/\u043c\u00b2, {layer.cost_per_m2} \u0440\u0443\u0431/\u043c\u00b2"
                    )
                if calc.notes:
                    lines.append(f"\n\u0417\u0430\u043c\u0435\u0442\u043a\u0438: {calc.notes}")
                self.txt_detail.setPlainText("\n".join(lines))
        except Exception as e:
            self.txt_detail.setPlainText(str(e))

    def _on_delete(self) -> None:
        calc_id = self._selected_id()
        if calc_id is None:
            QMessageBox.information(self, "\u0418\u0441\u0442\u043e\u0440\u0438\u044f", "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0437\u0430\u043f\u0438\u0441\u044c")
            return
        reply = QMessageBox.question(self, "\u0423\u0434\u0430\u043b\u0435\u043d\u0438\u0435", f"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0440\u0430\u0441\u0447\u0451\u0442 ID={calc_id}?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                HistoryService(session).delete_calculation(calc_id)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "\u041e\u0448\u0438\u0431\u043a\u0430", str(e))

    def _on_load(self) -> None:
        calc_id = self._selected_id()
        if calc_id is None:
            QMessageBox.information(self, "\u0418\u0441\u0442\u043e\u0440\u0438\u044f", "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0437\u0430\u043f\u0438\u0441\u044c")
            return
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                calc = HistoryService(session).get_calculation(calc_id)
                if not calc or not calc.snapshot_json:
                    QMessageBox.warning(self, "\u0418\u0441\u0442\u043e\u0440\u0438\u044f", "\u0421\u043d\u0438\u043c\u043e\u043a \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u0435\u0442")
                    return
                snapshot = json.loads(calc.snapshot_json)
                self.load_requested.emit(snapshot)
                QMessageBox.information(self, "\u0418\u0441\u0442\u043e\u0440\u0438\u044f", "\u0421\u043d\u0438\u043c\u043e\u043a \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d.\n\u041f\u0435\u0440\u0435\u0439\u0434\u0438\u0442\u0435 \u043d\u0430 \u0432\u043a\u043b\u0430\u0434\u043a\u0443 \u00ab\u0420\u0430\u0441\u0447\u0451\u0442\u00bb.")
        except Exception as e:
            QMessageBox.critical(self, "\u041e\u0448\u0438\u0431\u043a\u0430", str(e))

    def save_result(self, result) -> None:
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                calc_id = HistoryService(session).save_calculation(result)
            self.refresh()
            return calc_id
        except Exception as e:
            QMessageBox.warning(self, "\u0418\u0441\u0442\u043e\u0440\u0438\u044f", f"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c: {e}")
            return None
