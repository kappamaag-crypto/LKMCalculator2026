"""UI for source-linked engineering document search."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.normative import NormativeSource
from app.services.book_search_service import BookSearchResult, BookSearchService


class BookSearchView(QWidget):
    """Reference-only KB search; results always retain source identity."""

    source_selected = Signal(object)

    def __init__(self, books_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = BookSearchService(books_root)
        self._results: tuple[BookSearchResult, ...] = ()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Поиск по инженерным документам (справочный режим)"))
        layout.addWidget(
            QLabel(
                "Найденный текст не является автоматически подтверждённым нормативным правилом. "
                "Источник можно передать в инженерный контекст только как идентичность документа."
            )
        )

        self.query = QLineEdit()
        self.query.setPlaceholderText("Например: подготовка поверхности, Sa 2½, профиль...")
        self.query.returnPressed.connect(self.search)
        layout.addWidget(self.query)

        self.search_button = QPushButton("Искать")
        self.search_button.clicked.connect(self.search)
        layout.addWidget(self.search_button)

        self.rebuild_button = QPushButton("Перестроить индекс")
        self.rebuild_button.clicked.connect(self.rebuild)
        layout.addWidget(self.rebuild_button)

        self.source_button = QPushButton("Источник → контекст НД")
        self.source_button.setEnabled(False)
        self.source_button.setToolTip(
            "Передать выбранный документ в инженерный контекст без создания нормативных правил"
        )
        self.source_button.clicked.connect(self._handoff_source)
        layout.addWidget(self.source_button)

        self.status = QLabel("Индекс ещё не построен")
        layout.addWidget(self.status)

        self.results = QListWidget()
        self.results.currentRowChanged.connect(self._show_result)
        layout.addWidget(self.results)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)

    def rebuild(self) -> None:
        try:
            count = self.service.rebuild()
        except Exception as exc:
            self.status.setText(f"Ошибка индекса: {exc}")
            return
        self.status.setText(f"Индекс построен и сохранён в БД: {count} фрагментов")
        self.results.clear()
        self.preview.clear()
        self.source_button.setEnabled(False)
        self._results = ()

    def search(self) -> None:
        query = self.query.text().strip()
        if not query:
            self.status.setText("Введите поисковый запрос")
            return
        try:
            self._results = self.service.search(query)
        except Exception as exc:
            self.status.setText(f"Ошибка поиска: {exc}")
            return
        self.results.clear()
        for result in self._results:
            item = QListWidgetItem(f"{result.relative_path} · {result.locator}")
            self.results.addItem(item)
        self.preview.clear()
        self.status.setText(f"Найдено в БД: {len(self._results)}")
        self.source_button.setEnabled(bool(self._results))
        if self._results:
            self.results.setCurrentRow(0)

    def _show_result(self, row: int) -> None:
        if row < 0 or row >= len(self._results):
            self.preview.clear()
            self.source_button.setEnabled(False)
            return
        result = self._results[row]
        self.source_button.setEnabled(True)
        self.preview.setPlainText(
            f"Источник: {result.relative_path}\n"
            f"Позиция: {result.locator}\n"
            f"SHA-256: {result.sha256}\n\n"
            f"{result.text}"
        )

    def _handoff_source(self) -> None:
        row = self.results.currentRow()
        if row < 0 or row >= len(self._results):
            return
        result = self._results[row]
        source = NormativeSource(
            document_id=result.relative_path,
            title=result.relative_path,
            revision="",
            issuer="",
            source_uri="",
        )
        self.source_selected.emit(source)
        self.status.setText(
            "Источник передан в инженерный контекст как идентичность; нормативные правила остаются UNKNOWN."
        )
