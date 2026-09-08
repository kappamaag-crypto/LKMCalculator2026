# Этап 2. Архитектура новой версии

## Слои
- **domain/** — formulas, models, calculator, comparison, recommendation, validation
- **infrastructure/** — database (SQLAlchemy), export (Excel/PDF), logging
- **services/** — application services
- **ui/** — PySide6 GUI

## Принципы
- Формулы 1:1 со старым калькулятором
- Domain не зависит от UI
- Рекомендации — предварительные + дисклеймер

## Стек
Python 3.12+, PySide6, SQLAlchemy 2, openpyxl, reportlab, pytest
