# LKMCalculator 2026 v3.0 — план миграции

## Текущая архитектура

v3.0 развивается непосредственно в существующем `upload/`. Каталог `v2/` сохраняется как архив и не используется для запуска v3.

```text
UI (PySide6)
  ↓
Application / services
  ↓
Domain models + calculation engine
  ↓
SQLAlchemy repositories / ORM
  ↓
SQLite
```

Экспорт Excel/PDF, история, рекомендации и сравнение уже интегрированы в существующее приложение; новые функции должны подключаться через существующие сервисы, а не переносить расчёты в UI.

## Карта текущих файлов

| CURRENT FILE | CURRENT CLASS/FUNCTION | PROBLEM | REQUIRED CHANGE | PRIORITY |
|---|---|---|---|---|
| `upload/app/domain/models.py` | `Material`, `LayerDefinition`, `LayerResult`, `CoatingSystem`, `ObjectData`, result models | Доменная модель уже расширена, но отсутствуют полноценные сущности 2К, упаковки, среды, snapshot | Расширять существующие модели; не создавать `MaterialV3` | P0/P1 |
| `upload/app/domain/formulas.py` | DFT/WFT, dilution, losses, packaging | Расчётная логика есть, но промежуточное округление ещё встречается | Убрать промежуточное округление; округлять только presentation | P0 |
| `upload/app/domain/calculator.py` | `LayerCalculator`, `SystemCalculator` | Есть расчёт слоёв и систем; нет полноценного 2К pipeline | Интегрировать 2К через отдельный domain service | P0 |
| `upload/app/domain/validation.py` | `validate_material`, `validate_layer_input` | Уже проверяет диапазоны; не хватает технологического контроля объекта/фактического DFT | Добавить `TechnologyCheckService` | P1 |
| `upload/app/domain/recommendation/rules.py` | hard filters | Hard filter уже отделён от score | Расширить химическую среду, технологические ограничения и совместимость | P1 |
| `upload/app/domain/recommendation/scorer.py` | scoring | Score уже не спасает систему, провалившую hard filter | Вынести веса в конфигурацию | P1 |
| `upload/app/domain/comparison.py` | comparison | Сравнение уже учитывает стоимость/слои | Расширить 2К, закупку и технологические показатели | P1 |
| `upload/app/infrastructure/database/models.py` | SQLAlchemy ORM | Существующие таблицы есть, но часть новых полей/сущностей отсутствует | Добавлять additive schema changes | P0/P1 |
| `upload/app/infrastructure/database/repositories.py` | repository layer | Материалы и расчёты уже имеют репозитории; часть новых сущностей не поддерживается | Добавлять repositories/serializers без дублирования | P1 |
| `upload/app/infrastructure/database/engine.py` | `init_db` | Используется `create_all`, Alembic отсутствует | Добавить миграционный слой без destructive migration | P0 |
| `upload/app/ui/main_window.py` | `MainWindow` | Workflow уже существует | Только подключать новые сервисы/views | P1/P2 |
| `upload/app/ui/views/calculation_view.py` | calculation UI | Недавно исправлены Excel/PDF/comparison actions | Не ломать существующий UI; расширять результат | P1/P2 |
| `upload/app/infrastructure/export/*` | Excel/PDF exporters | Экспорт уже есть | Расширить листы/отчёт после стабилизации domain | P2 |
| `upload/tests/*` | unit/regression tests | Есть формулы, dilution, recommendation tests | Расширить 2К, packaging, technology, snapshots | P0/P1 |

## Уже выполнено до этого плана

- v3.0 versioning в `upload/`.
- Явная база разбавления.
- Разделение расхода исходного ЛКМ и разбавителя.
- Hard-filter recommendation logic.
- Comparison без принципа «толще = лучше».
- Расширенная валидация.
- Исправлен экспорт Excel/PDF и переход к сравнению из calculation view.

## Порядок дальнейшей реализации

1. **P0. Расчётный движок:** точность без промежуточного округления, UNKNOWN/None, единицы, regression tests.
2. **P0. 2К:** `MaterialComponent`, `MaterialMix`, component/package calculation; отдельный domain service.
3. **P0. Фасовка:** `Package`, комплекты для 2К, остаток и закупочный резерв.
4. **P0/P1. БД:** additive migration strategy; сохранить существующие SQLite записи.
5. **P1. Object/Environment:** ChemicalExposure, ISO environment/durability, расширенные поверхности.
6. **P1. Technology:** точка росы, RH, температура, шероховатость, подготовка, DFT actual/recoat.
7. **P1. Recommendation:** химия/технология/compatibility hard filters + configurable score weights.
8. **P1. Pricing:** material/application/preparation/equipment/inspection/logistics/overhead/margin.
9. **P2. Excel:** 9 листов + version/formula/date.
10. **P2. PDF:** print-ready technical/commercial report.
11. **P2. UI:** подключение новых данных без переноса расчётов в UI.
12. **P3. Geometry/import/OGZ/floors:** только после стабилизации v3 core.

## Правило каждого этапа

Перед переходом дальше:

- unit/regression tests;
- smoke-check запуска приложения;
- проверка БД на существующих данных;
- отдельный commit;
- фиксация рисков и изменений.

## Ограничение 2К

2К расчёт реализуется как инженерная модель компонентов/смеси/комплектов. Он не должен превращаться в CRM/ERP. В расчётном результате отдельно видны потребность компонентов, закупка комплектов, остаток и стоимость.
