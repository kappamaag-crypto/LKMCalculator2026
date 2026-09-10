"""Вкладка истории расчётов."""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QTextEdit, QSplitter,
)
from PySide6.QtCore import Qt, Signal

from app.infrastructure.database.engine import get_session_factory, session_scope, init_db, get_engine
from app.services.history_service import HistoryService
from app.services.notification_service import enqueue_event
from app.config import DB_PATH


class HistoryView(QWidget):
    """История сохранённых расчётов."""

    load_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db_path = DB_PATH
        self._build_ui()
        self.refresh()

    def _get_session_factory(self):
        path = self._db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = get_engine(path)
        init_db(engine)
        return get_session_factory(engine)

    @staticmethod
    def _money(value, decimals=2) -> str:
        if value is None:
            return "—"
        return f"{value:,.{decimals}f}".replace(",", " ")

    @staticmethod
    def _value(value) -> str:
        return "—" if value is None else str(value)

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
        for button in (btn_refresh, btn_delete, btn_load):
            btn_row.addWidget(button)
        btn_row.addStretch()
        root.addLayout(btn_row)

        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "№", "Объект", "Система", "DFT, мкм", "Стоимость, руб"])
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
        self.txt_detail.setMaximumHeight(240)
        splitter.addWidget(self.txt_detail)
        root.addWidget(splitter)

    def refresh(self) -> None:
        self.table.setRowCount(0)
        self.txt_detail.clear()
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                rows = HistoryService(session).list_calculations(limit=200)
                self.table.setRowCount(len(rows))
                for r, calc in enumerate(rows):
                    date_str = calc.created_at.strftime("%d.%m.%Y %H:%M") if calc.created_at else "—"
                    values = [
                        str(calc.id), date_str, calc.calculation_number or "—",
                        calc.object_name or "—", calc.system_name or "—",
                        self._money(calc.total_dft, 0), self._money(calc.total_cost, 0),
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
        return item.data(Qt.UserRole) if item is not None else None

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
                    f"ID: {calc.id}", f"Дата: {calc.created_at}", f"№: {calc.calculation_number or '—'}",
                    f"Объект: {calc.object_name or '—'}", f"Заказчик: {calc.customer or '—'}",
                    f"Проект: {calc.project or '—'}", f"Система: {calc.system_name or '—'}",
                    f"Площадь: {self._value(calc.area_m2)} м²", f"DFT: {self._money(calc.total_dft, 0)} мкм",
                    f"Расход: {self._value(calc.total_consumption_kg)} кг/м²",
                    f"Стоимость: {self._money(calc.total_cost_per_m2)} руб/м²",
                    f"Стоимость объекта: {self._money(calc.total_cost, 0)} руб", "", "Слои:",
                ]
                for layer in calc.layers:
                    lines.append(
                        f"  {layer.layer_number}. {layer.material_name}: "
                        f"DFT={self._money(layer.dry_thickness, 0)} мкм, "
                        f"{self._value(layer.consumption_kg)} кг/м², "
                        f"{self._money(layer.cost_per_m2)} руб/м²"
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
        reply = QMessageBox.question(self, "Удаление", f"Удалить расчёт ID={calc_id}?", QMessageBox.Yes | QMessageBox.No)
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
                service = HistoryService(session)
                snapshot = service.get_calculation_snapshot(calc_id)
                self.load_requested.emit(snapshot)
            QMessageBox.information(self, "История", "Проверенный снимок загружен в форму расчёта.")
        except (KeyError, ValueError) as e:
            QMessageBox.critical(self, "Ошибка снимка", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def save_result(self, result) -> Optional[int]:
        try:
            sf = self._get_session_factory()
            with session_scope(sf) as session:
                calc_id = HistoryService(session).save_calculation(result)
                recipient = os.getenv("LKM_NOTIFICATION_RECIPIENT", "").strip()
                if recipient:
                    enqueue_event(
                        session,
                        "calculation_saved",
                        calc_id,
                        recipient,
                        f"LKM Calculator: сохранён расчёт №{result.object_data.calculation_number or calc_id}",
                        "Сохранён расчёт в истории LKM Calculator.\n"
                        f"ID: {calc_id}\n"
                        f"Объект: {result.object_data.object_name or '—'}\n"
                        f"Система: {result.system.system_name or '—'}",
                    )
            self.refresh()
            return calc_id
        except Exception as e:
            QMessageBox.warning(self, "История", f"Не удалось сохранить: {e}")
            return None
