"""
Точка входа — Калькулятор ЛКМ / АКЗ v3.0
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ensure_directories
from app.infrastructure.logging_setup import setup_logging
from app.infrastructure.database.engine import init_db, get_session_factory
from app.infrastructure.database.seed import run_seed
from app.services.notification_worker import NotificationWorker


def main() -> None:
    ensure_directories()
    setup_logging()
    init_db()

    # Начальное заполнение выполняется один раз при запуске приложения,
    # а не из отдельных экранов. Seed идемпотентен.
    session_factory = get_session_factory()
    with session_factory() as session:
        run_seed(session)
        # Worker одноразовый и opt-in: обычный запуск приложения не требует
        # SMTP и не создаёт фонового daemon/thread.
        NotificationWorker.run_once(session)

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from app.ui.main_window import MainWindow
    from app import __app_name__, __version__

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("LKM Calculator")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
