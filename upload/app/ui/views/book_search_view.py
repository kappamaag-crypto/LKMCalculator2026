"""UI for source-linked engineering document search."""
from __future__ import annotations

from pathlib import Path

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

from app.services.book_search_service import BookSearchResult, BookSearchService


class BookSearchView(QWidget):
    """Reference-only KB search; results always retain source identity."""

    def __init__(self, books_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = BookSearchService(books_root)
        self._results: tuple[BookSearchResult, ...] = ()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Поиск по инженерным документам (справочный режим)"))

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
        self.status.setText(f"Индекс построен: {count} фрагментов")
        self.results.clear()
        self.preview.clear()

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
        self.status.setText(f"Найдено: {len(self._results)}")
        if self._results:
            self.results.setCurrentRow(0)

    def _show_result(self, row: int) -> None:
        if row < 0 or row >= len(self._results):
            self.preview.clear()
            return
        result = self._results[row]
        self.preview.setPlainText(
            f"Источник: {result.relative_path}\n"
            f"Позиция: {result.locator}\n"
            f"SHA-256: {result.sha256}\n\n"
            f"{result.text}"
        )
