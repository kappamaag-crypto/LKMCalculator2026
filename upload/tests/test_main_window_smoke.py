"""Headless smoke regression for the v3 main window shell."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def test_main_window_builds_all_primary_tabs_and_actions():
    _app()
    window = MainWindow()

    expected_tabs = [
        "Расчёт",
        "Сценарий",
        "Рекомендации",
        "Сравнение",
        "2К-информация",
        "База материалов",
        "Системы",
        "Каталог систем",
        "История",
        "Инженерная БД",
        "Инспекция",
        "Настройки",
    ]

    assert window.tabs.count() == len(expected_tabs)
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == expected_tabs
    assert window.calc_view is window.tabs.widget(0)
    assert window.cmp_view is window.tabs.widget(3)
    assert window.inspection_view is window.tabs.widget(10)
    assert window.settings_view is window.tabs.widget(11)

    engineering_menu = next(
        action.menu() for action in window.menuBar().actions() if action.text() == "Инженерное"
    )
    assert engineering_menu is not None
    assert {
        action.text() for action in engineering_menu.actions()
    } >= {
        "Контекст НД и поверхности…",
        "Pre-Application Check…",
        "Химстойкость…",
        "Пояснение расчёта…",
        "Инженерная БД…",
        "Каталог систем 1–4…",
        "Инспекция / контроль качества…",
    }

    window.close()
