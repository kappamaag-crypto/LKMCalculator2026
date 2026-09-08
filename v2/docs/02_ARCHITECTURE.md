# Этап 2. Архитектура новой версии

## Цели

- Профессиональный инженерный инструмент подбора и сравнения систем АКЗ
- Модульность, тестируемость, расширяемость
- Сохранение математики старого калькулятора 1:1
- Современный GUI (PySide6)
- Полноценная БД + рекомендации + PDF + Excel

## Структура проекта

```
lkm_calculator/
├── main.py
├── requirements.txt
├── README.md
├── docs/
│   ├── 01_AUDIT.md
│   ├── 02_ARCHITECTURE.md
│   ├── 03_MIGRATION.md
│   └── ...
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── constants.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── enums.py
│   │   ├── models.py              # dataclass / Pydantic
│   │   ├── formulas.py            # ВСЕ формулы
│   │   ├── calculator.py
│   │   ├── validation.py
│   │   ├── comparison.py
│   │   └── recommendation/
│   │       ├── __init__.py
│   │       ├── rules.py
│   │       ├── scorer.py
│   │       └── recommender.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py
│   │   │   ├── models.py          # SQLAlchemy
│   │   │   ├── repositories.py
│   │   │   └── seed.py
│   │   ├── export/
│   │   │   ├── excel_exporter.py
│   │   │   └── pdf_exporter.py
│   │   └── logging_setup.py
│   ├── services/
│   │   ├── calculation_service.py
│   │   ├── recommendation_service.py
│   │   ├── history_service.py
│   │   ├── material_service.py
│   │   └── system_service.py
│   └── ui/
│       ├── main_window.py
│       ├── views/
│       ├── dialogs/
│       ├── widgets/
│       └── resources/
├── data/
│   ├── database.sqlite
│   └── backups/
├── tests/
└── logs/
```

## Слои ответственности

| Слой | Ответственность |
|------|-----------------|
| **domain** | Чистая бизнес-логика, формулы, модели, правила рекомендаций. Без GUI и БД. |
| **infrastructure** | SQLAlchemy, openpyxl, reportlab, файловая система |
| **services** | Application services — оркестрация use-cases |
| **ui** | Только представление и пользовательский ввод |

## Ключевые принципы

1. Формулы только в `domain/formulas.py`
2. Модели — dataclass / Pydantic, никаких list-индексов
3. Repository pattern для доступа к данным
4. Все расчёты покрыты unit-тестами
5. История — только в SQLite
6. Рекомендации — двухступенчатые (фильтр → scoring)

## Основные сущности domain

- Material
- Layer
- LayerResult (результат расчёта слоя)
- CoatingSystem
- Calculation
- CalculationResult
- ComparisonResult
- RecommendationResult
- ProjectData / ObjectData (входные данные)

## Технологический стек

- Python 3.12+
- PySide6
- SQLAlchemy 2.x
- openpyxl
- reportlab
- matplotlib
- pytest
- pydantic (опционально, для валидации)
