# План развития LKMCalculator — АКЗ / ОГЗ / инженерный режим

> Живой план для ветки `v3.0-engineering-upgrade`.

## Правила
1. Не ломать расчёт.
2. Инженерная логика — domain/service.
3. Excel не второй движок.
4. PDF/Excel из одного результата.
5. Не смешивать инженерные/коммерческие данные.
6. Regression до закрытия.
7. Code commit, затем docs.
8. `ВЫПОЛНЕНО` с доказательством.
9. Отсутствующие = `UNKNOWN`.
10. GitHub Actions не запускать.
11. SPKEFFA read-only.

## Матрица статуса

| § | Статус | Состояние |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро. |
| 2 | ЧАСТИЧНО | UI smoke — PySide6. |
| 3 | ВЫПОЛНЕНО | AdHocMaterialDialog. |
| 4 | ЧАСТИЧНО | Comparison/2K. |
| 5 | ЧАСТИЧНО | Engineering Excel. |
| 6 | ЧАСТИЧНО | PDF. |
| 7 | ВЫПОЛНЕНО | Precision. |
| 8 | ВЫПОЛНЕНО | 2K. |
| 9 | ВЫПОЛНЕНО | PackagingPlanner. |
| 10 | ВЫПОЛНЕНО | Alembic + backup. |
| 11 | ВЫПОЛНЕНО | Snapshot integrity. |
| 11.1 | ВЫПОЛНЕНО | Outbox. |
| 12 | ЧАСТИЧНО | Engineering context. |
| 13 | ЧАСТИЧНО | Surface condition. |
| 14 | ЧАСТИЧНО | SPKEFFA rules. |
| 15 | IN_PROGRESS | PTM: реализован отдельный domain/service/UI-контур; добавлены требуемые категории сортамента и стандарты, автоматический пересчёт F/P/PTM/м²·м/м²·т, режимы 2/3/4 сторон и ручные размеры для размерных профилей. Полные табличные данные всех перечисленных стандартов ещё не импортированы и требуют source-backed заполнения. ОГЗ отдельно и пока не входит в расчёт ПТМ. |
| 16 | ЧАСТИЧНО | Recommendations. |
| 17 | ЧАСТИЧНО | Inspection DFT UI. |
| 18 | ЧАСТИЧНО | Evidence log; full suite green: 513 passed, 3 skipped. |
| 19 | ВЫПОЛНЕНО | Legacy parity. |
| 20 | ЧАСТИЧНО | KB / Системы. Системы 1–4 не удалось прочитать; причина/обходной путь пока не подтверждены. |
| 21 | ЧАСТИЧНО | Compatibility. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | LKM-Prof Table 1. Материал: полная инженерная карточка и полный scalar ORM↔domain mapping реализованы; regression round-trip добавлен. Скрытые ORM defaults для `thinner_basis` и `thinner_required` устранены; добавлены regression guards на `nullable=True` и отсутствие Python/server default. TDS URL не является обязательным: инженерные параметры вводятся вручную, отсутствующие остаются `UNKNOWN`. Осталось execution-proof + полный аудит Table 1 на скрытые значения. |
| 23 | ВЫПОЛНЕНО | Pre-Application domain/service. |
| 24 | ВЫПОЛНЕНО | Source-backed only; empty⇒UNKNOWN; promote gate; conc/temp limits. Evidence: `test_chemical_resistance.py` (12). Agent catalog expansion remains §25. |
| 25 | ЧАСТИЧНО | Catalog KNOWN. |
| 26 | ВЫПОЛНЕНО | Explanation Engine domain/service wired; regression tests, dialog smoke and main-window acceptance smoke are execution-proven by full suite: 513 passed, 3 skipped. |
| 27 | ЧАСТИЧНО | Staging. |
| 28 | ВЫПОЛНЕНО | LossProfile. |
| 29 | ЧАСТИЧНО | confirm_draft. |
| 30 | ВЫПОЛНЕНО | Decision Log. |
| 31 | ЧАСТИЧНО | Scenario. |
| 32 | ВЫПОЛНЕНО | DFT inspection domain/service workflow, headless UI smoke and regression coverage are execution-proven by full suite: 513 passed, 3 skipped. |
| 33 | IN_PROGRESS | Universal Excel discovery + RAL-aware material identity implemented in importer/seed/repository/UI; execution-proof and full rebuild with all source books still required. |

## Stages

- §22 remains open: engineering material card and repository mapping are implemented; ORM hidden defaults for `MaterialORM.thinner_basis` and `MaterialORM.thinner_required` are removed and guarded by regression. §22 is not marked complete until local regression execution and the LKM-Prof Table 1 hidden-value audit are proven.
- §20 remains partial: Systems/KB work is not complete; systems 1–4 could not be read, and the reason/workaround has not yet been technically confirmed.
- §23/§24 domain closed.
- §26 closed: domain/service + regression + dialog smoke + main-window acceptance test are implemented and execution-proven by the green local full suite.
- §32 closed: DFT domain/service workflow and headless UI smoke are implemented; regression coverage for missing acceptance bands ⇒ `UNKNOWN`, missing measured value ⇒ `UNKNOWN`, out-of-range evaluation, and the invariant that DFT binding does not auto-set inspection acceptance is execution-proven by the green local full suite.
- Full local suite previously proven: `513 passed, 3 skipped, 49 warnings in 6.42s`.
- SPKEFFA read-only.


## §33. Каталог материалов: универсальные Excel-источники и RAL-варианты

**Статус: IN_PROGRESS — код реализован, execution-proof ещё не закрыт**

### 33.1 Универсальное обнаружение Excel

Папка `books/` является входным каталогом источников ЛКМ.

Требование:
- импортёр не должен зависеть от фиксированного списка из пяти книг;
- автоматически обнаруживать новые `.xls`, `.xlsx`, `.xlsm` (при поддержке формата);
- просматривать все листы и определять таблицы/строки с материалами по заголовкам и содержимому;
- сохранять исходный файл, лист, строку, колонку и все непустые исходные ячейки;
- неизвестные поля не выбрасывать: сохранять их в source/provenance;
- отсутствие распознанного инженерного параметра = `UNKNOWN`, а не догадка;
- новый Excel в `books/` должен попадать в следующий rebuild без ручного добавления имени файла в код;
- дубли между источниками не удалять автоматически.

### 33.2 RAL-варианты

Один базовый материал может иметь варианты цвета/RAL, например:

```text
Blank Finish
 ├─ RAL 7035 → цена X
 ├─ RAL 7040 → цена Y
 └─ RAL 9005 → цена Z
```

Технические характеристики могут быть общими: плотность, объёмный сухой остаток, DFT, расход, времена сушки и другие инженерные параметры. **Цена может отличаться для каждого RAL и не должна усредняться или подменяться ценой другого RAL.**

### 33.3 Правило идентичности

`material_name` нельзя считать единственным ключом. Необходимо различать:
1. базовую техническую идентичность;
2. вариант исполнения/цвет;
3. RAL;
4. коммерческую цену варианта;
5. источник и версию/дату источника.

Одинаковый материал с RAL 7035 и RAL 7040 должен сохранять оба коммерческих варианта, даже если технические параметры совпадают.

### 33.4 Наследование

Если источник явно показывает, что RAL являются вариантами одного материала, инженерные характеристики могут быть общими на уровне базового материала, но цена остаётся на уровне варианта. Если конкретный RAL имеет отдельные технические данные, они не должны автоматически распространяться на остальные RAL.

### 33.5 Расчёт

При выборе RAL калькулятор использует цену именно выбранного RAL. Отсутствие цены конкретного RAL = `UNKNOWN`; цена другого RAL не подставляется. Изменение RAL не должно требовать ручного дублирования инженерных характеристик.

### 33.6 Regression

Обязательны тесты: два RAL с разными ценами; одинаковые характеристики; отсутствующая цена; отдельные характеристики одного RAL; одинаковый материал/RAL из разных источников; защита от перезаписи второго RAL; защита от схлопывания RAL при rebuild.

### 33.7 Реализовано в коде

- `books/` автоматически сканируется для `.xls`, `.xlsx`, `.xlsm`;
- RAL извлекается как из отдельной колонки, так и из названия материала;
- packed/slash values для RAL распределяются по соседним материалам;
- идентичность импортируемой записи учитывает `material_name + RAL`;
- seed больше не перезаписывает RAL 7035 данными RAL 7040;
- RAL отображается в `Material.display_name()` и в таблице базы материалов;
- repository/UI сохраняют варианты по `name + RAL`;
- цена остаётся на уровне выбранного RAL и не усредняется между вариантами.

### 33.8 Закрытие §33

До `DONE` необходимо определить `MaterialVariant` либо эквивалентную модель, изменить importer/seed/repository, сохранить обратную совместимость БД, выполнить regression + smoke и подтвердить результат.


### §33 implementation checkpoint

Реализовано в коде:
- автоматическое обнаружение `.xls`, `.xlsx`, `.xlsm` в `books/`;
- один технический материал может содержать несколько `MaterialVariant`;
- RAL/цвет не используется как повод дублировать техническую карточку;
- цена за кг/литр хранится на уровне конкретного варианта;
- при нескольких RAL базовая цена не используется как подмена цены варианта;
- импорт сохраняет provenance варианта;
- Alembic migration `012_material_variants`;
- `CalculationView` показывает RAL-варианты как отдельные выбираемые позиции расчёта;
- добавлены regression checks для двух RAL с одинаковыми инженерными параметрами и разными ценами.

Статус остаётся `IN_PROGRESS` до запуска локального rebuild + migration + test suite и smoke-проверки приложения.
