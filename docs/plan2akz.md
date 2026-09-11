# План развития LKMCalculator — АКЗ / ОГЗ / инженерный режим

> Живой план для ветки `v3.0-engineering-upgrade`. Статус меняется только по фактическому состоянию кода и проверок.

## Правила
1. Не ломать существующий расчёт.
2. Инженерная логика находится в domain/service, а не в UI.
3. Excel не является вторым расчётным движком.
4. PDF и Excel получают данные из одного `CalculationResult` / `SystemCalculationResult`.
5. Инженерные и коммерческие/закупочные данные не смешивать без явного назначения.
6. Существенный этап должен иметь regression/smoke-проверку.
7. Каждый существенный этап — отдельный code commit.
8. После code commit — отдельный commit с фиксацией результата в этом плане.
9. `ВЫПОЛНЕНО` ставится только при наличии реализации и тестового/CI или явного smoke-доказательства.
10. При отсутствии исходных данных использовать `UNKNOWN`, не придумывать запрет/разрешение.
11. GitHub Actions для текущей работы не запускать; локальные/статические проверки должны быть явно обозначены.

## Матрица статуса

| § | Статус | Фактическое состояние / доказательство |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро расчёта сохранено. |
| 2 | ЧАСТИЧНО | Динамический редактор существует; workflow совместимости и визуальный smoke остаются. |
| 3 | ВЫПОЛНЕНО | `AdHocMaterialDialog`: нормализация, duplicate reuse, persistence; regression `42bb7fb`. Новые табличные источники «Системы 1–4» определены как отдельный вход для будущего импорта материалов, но импорт из них ещё не реализован. |
| 4 | ЧАСТИЧНО | ComparisonEngine/View, 2K/многослойность и headless UI smoke `2ad50af`; остаются визуальный smoke и финальная source-backed проверка wording. |
| 5 | ЧАСТИЧНО | Инженерный Excel и regression missing-price `a1e1a0a`; остаются визуальный/печать/PDF-конверсионный smoke. |
| 6 | ЧАСТИЧНО | PDF строится из `SystemCalculationResult`; multilayer/comparison/2K/unknown-price покрыты; cross-export regression `e3ef08`; остаются визуальный/печать smoke. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants + независимые golden cases 2/3/4/5 layers; исторически был успешный CI. |
| 8 | ВЫПОЛНЕНО | 2K учитывается как один смешанный материалный слой; TDS technology rules вынесены в §14. |
| 9 | ЧАСТИЧНО | `PackagingPlanner` считает коммерческую потребность по фасовке: целые упаковки, резерв и опциональную стоимость. Складские остатки, складской учёт, резерв склада и закупочные заказы не входят. |
| 10 | ЧАСТИЧНО | Alembic + SQLite-safe backup/restore; acceptance отложен. Необратимые downgrade требуют восстановления backup. |
| 11 | ЧАСТИЧНО | Self-contained immutable material snapshots v5, verified reads и integrity hashing реализованы; acceptance/runtime smoke отложен. |
| 11.1 | ЧАСТИЧНО | Durable notification outbox интегрирован с `calculation_saved`; opt-in worker/trigger, idempotency metadata и env-only SMTP реализованы. SMTP/runtime smoke и тесты отложены. |
| 12 | ЧАСТИЧНО | Normative foundation + source-preserving serializer + History snapshot v7 реализованы. `SystemCalculationResult` типизированно содержит `EngineeringContext`; `SystemCalculator`, `CalculationService` и `CalculationView` принимают/переносят его явно. History умеет сохранять и восстанавливать typed context, включая legacy v6. В UI есть редактор source identity и реестр доступных source-документов. Добавлен безопасный verified sidecar loader с SHA-256 и registry assembly с duplicate protection. Фактический набор verified rules/manifest пока не добавлен. Acceptance отложен. |
| 13 | ЧАСТИЧНО | `SurfacePreparation`, `SurfaceProfile`, `SurfaceCondition` + serializer и History snapshot v7 реализованы. `CalculationView` хранит/восстанавливает typed surface context; legacy fallback сохранён. В UI есть редактор подготовки/профиля и источников. Без источника assessment остаётся `UNKNOWN`. Acceptance отложен. |
| 14 | НЕ ВЫПОЛНЕНО | Полная TDS-backed technological validation. Начинать после появления проверяемого source-backed rule pipeline. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Legacy recommendation hard-filter/score; `RecommendationEngine` дополнительно прогоняет разрешённые системы через `LayerCompatibilityEngine` и переносит source-backed warnings/limitations. `UNKNOWN` и отсутствие подтверждённого правила не изменяют ranking; environment/technology/весовые настройки и полноценная compatibility scoring остаются. |
| 17 | ЧАСТИЧНО | Typed inspection domain/service, regression cases и UI-вкладка реализованы. UI commit `16c3825cb6a913dd36c216e79987c615ce476fae`. Приёмочный статус по умолчанию `UNKNOWN`; нормативные критерии не выводятся автоматически. Runtime/UI acceptance ещё не выполнены. |
| 18 | ЧАСТИЧНО | Добавлен release acceptance checklist `docs/release_acceptance_v3.md` с отдельными пунктами regression, UI smoke, compatibility, inspection, persistence, DB backup/restore, Excel/PDF и документации. Все пункты пока `PENDING`; сам release acceptance не выполнен. |
| 19 | ЧАСТИЧНО | Добавлен `docs/legacy_parity_matrix_v3.md` с явной матрицей сравнения v2→v3 по расчёту, 2K, persistence, history, recommendations, Excel/PDF и UI. Строки пока `PENDING`; parity acceptance не выполнен. |
| 20 | ЧАСТИЧНО | `book_index.py` индексирует source identity/integrity файлов `books/`; `book_content_index.py` извлекает searchable content из PDF и UTF-8 text-like файлов в source-linked chunks с path/SHA-256/locator; `BookSearchService` имеет DB-backed persistence/search; `BookSearchView` подключён отдельной вкладкой и меню, показывает source/locator/SHA-256, а выбранный источник можно передать в инженерный контекст как `UNKNOWN` source identity без создания нормативного значения. В `books/` добавлены табличные источники `Системы 1.xls`, `Системы 2.XLSX`, `Системы 3.xlsx`, `Системы 4.xlsx`; они должны рассматриваться как структурированные источники для каталога систем и кандидатов материалов, с сохранением имени файла/пути/хэша и без автоматического признания данных нормативными. Остаются acceptance/visual smoke и более глубокая интеграция KB с инженерными решениями. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix есть; applicability к реальной chemistry/TDS остаётся. Системные таблицы могут быть входом для вариантов систем, но не заменяют TDS/нормативный источник. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | `LayerCompatibilityEngine` подключён к `CalculationService.format_summary()` и напрямую к `SystemsView`: редактор показывает source-backed статус и переходы, обновляя их при изменении слоёв. `RecommendationEngine` также переносит compatibility warnings/limitations без изменения ranking. Семантика уточнена: только явно запрещённый source-backed переход является blocker; `WARNING` и `UNKNOWN` требуют инженерной проверки и не превращаются в автоматический запрет. Остаются UI regression/acceptance и TDS-backed conditions. |
| 23 | НЕ ВЫПОЛНЕНО | Pre-Application Check / технологическая готовность — P1. |
| 24 | НЕ ВЫПОЛНЕНО | Химическая стойкость и среда эксплуатации — P1. |
| 25 | НЕ ВЫПОЛНЕНО | Нормативная traceability — P1. |
| 26 | НЕ ВЫПОЛНЕНО | Explanation Engine — P1. |
| 27 | НЕ ВЫПОЛНЕНО | Material Data Quality / полнота карточек — P1. В рамках этого этапа добавить контроль импорта из табличных источников «Системы 1–4»: сопоставление колонок, обязательные поля, duplicate detection, происхождение значения и разделение данных системы от данных карточки материала. |
| 28 | НЕ ВЫПОЛНЕНО | Loss Profile / расход и потери — P1. |
| 29 | НЕ ВЫПОЛНЕНО | System Templates / каталог типовых систем — P2. Источники «Системы 1–4» являются исходным материалом для этого этапа: каждая строка/вариант системы должна потенциально преобразовываться в инженерный шаблон из слоёв; из названий материалов должны формироваться кандидаты на добавление в БД материалов. Импорт должен быть staging/review workflow, а не безусловной записью в БД. |
| 30 | НЕ ВЫПОЛНЕНО | Engineering Decision Log — P2. |
| 31 | НЕ ВЫПОЛНЕНО | Calculation Scenarios / инженерные сценарии — P2. В перспективе варианты из «Системы 1–4» могут использоваться как исходные варианты сценариев, но сами таблицы не являются отдельным расчётным движком. |
| 32 | НЕ ВЫПОЛНЕНО | Inspection / фактический DFT workflow — P2. |

## Последние code-этапы

### §12/§13 — Engineering context and persistence foundation
Code commits: `709eadea3be513fb3a2a540dc195ef93956f4b09`, `6d3c86145f65ac339a98382eb50d7f21ef200142`, `4a623ed5bf0b19d34bb57009135f8b96b54cb634`, `7d4d40e6b6985a159b9a998438db32ca79ed4c14`, `70ec88eb28101e3a78f332f9be10303c22a9b320`, `d31971c5b725da2b2ff351500c70b4d269ac5ceb`, `c63fc757fed36249f25b7eb6384fb6f69bd00547`, `6e112c2621af2adef23b4d72c4025bfdb627543c`, `b545603bef83dfb10b346516f9f19a7b305d8494`, `98d3fe008f420067ee8db8ae30447682d5c273c`.

### §12/§13 — UI source/context workflow
Code commits: `4f9175755f8e43100b80f4f43cddf58a3248ef4a`, `cd58fa3ee2d24d3a5eeb7d1140aea3d4a231180a`, `608f84c0501cd57f147c876a23417990fca13ab8`, `27d7cff3194564728682bf330a651b31163e0a34`, `6db6da2b5a72d9d93a2bbd6ea8a4572c2dc0e916`.

### §12 — Verified source-backed rule boundary
Code commits: `f425ab1ed46697807f0c0c1414429f2ac631e872`, `76f5c6ad5f65ac339a98382eb50d7f21ef200142`.

### §20 — Repository book source/content/search foundation
Code commits: `1c0fe4e83d4d02c7fd9828547bc7e45a669ffc28`, `5805f111719b5b664d01a447d9e76596d5393cda`, `83f12f8b0eb2d261ac04f19a257e4a91553fc028`, `2c084a315d27b5bc181ff57177a1cdae6c02dcaa`.

### §20 — Source-linked engineering KB view
Code commits: `bd69c39d25f5f47747cfb3de871ae5d795ee83f7`, `6916dae0493be9afbeacff4f6f67d4435942cd72`.

### §20 — DB-backed engineering KB
Code commits: `a44b892d2260bbf7a72b600ba2cbbc33318553f5`, `d08a867eb1b0c8e6343028a330df0e4978fee05f`, `085ff829c769632b5aabd7fcd20048b62ed8eabf` — ORM persistence/search chunks, Alembic `006_engineering_book_chunks` и DB-backed `BookSearchService`.

### §20 — KB source handoff to engineering context
Code commits: `b47743a679edd147848d6aab3f4b5088f10365cd`, `3929540e50bc2f69c40d84c5e308e39591ec6095`, `701cc385a2d4e68716b3d992919e41524bed3cf5` — источник из справочной БД передаётся в инженерный контекст только как source identity; source-only состояние хранится через явное `UNKNOWN` правило.

### §22 — Calculation workflow integration
Code commit: `2ea726933b859c8e00dd17069be437cb6251a302` — `CalculationService` получил `LayerCompatibilityEngine`; `compatibility_report()` и source-backed блок совместимости добавлены в `format_summary()`.

### §22 — Systems workflow integration
Code commit: `d4db7ee7c87478a280de79412fc86dd176ddb8a7` — `SystemsView` получил прямую source-backed проверку соседних слоёв. Редактор показывает сводный статус и детализацию переходов, автоматически обновляя её при изменении состава/порядка слоёв. `UNKNOWN` не превращается в запрет; TDS-условия не интерпретируются.

### §16/§22 — Recommendation compatibility explanation
Code commit: `99c1643d0a823963e730df730ff73864860ec2f5` — `RecommendationEngine` получает `LayerCompatibilityEngine`, проверяет resolved layers прошедших hard-filter систем и переносит source-backed compatibility warnings/limitations в `RecommendationItem`; `UNKNOWN` не меняет ranking.

### §22 — Compatibility status semantics
Code commits: `1817249358e613bd753a431c617f7a35f24dd881`, `063ef315cd37d6bbcf1bad45d3e15bcf72db519b` — `LayerCompatibilityReport` разделяет `WARNING`, `UNKNOWN` и явно `FORBIDDEN`; `blocking_transitions` сохранён как обратимо-совместимый alias только для `FORBIDDEN`. Recommendation workflow больше не трактует WARNING/UNKNOWN как blockers.

### §17 — Inspection workflow foundation
Code commits: `8408933facba7f93d05f4ae745cb9b4de78f70d2` — typed `InspectionRecord`, `InspectionMeasurement`, `InspectionDefect`; `9a6667d29861b122e6160990dab889eaf8c95eed` — `InspectionService`; `eab29520a26b406839bdcff8cba39a3626d827a0` — regression cases; `16c3825cb6a913dd36c216e79987c615ce476fae` — UI-вкладка и пункт меню.

### §18/§19 — Release and parity acceptance foundation
Docs commit: `fc6cbdb8286ed29fa2f2fbc52363710621373a43` — release acceptance checklist и legacy parity matrix. Acceptance evidence remains pending.

## §22 — Критическое ограничение
Не закрывать §22 до фактического пользовательского acceptance.

Минимум для закрытия:
1. интеграция проверки в `CalculationView` — выполнена через `CalculationService.format_summary()`;
2. интеграция проверки в `SystemsView`/редактор системы — выполнена в code commit `d4db7ee7c87478a280de79412fc86dd176ddb8a7`;
3. UI regression на положительный, отрицательный и `UNKNOWN` сценарии — остаётся;
4. условия `previous_is_cured`, `recoat_elapsed_h`, `surface_prepared` только если они подтверждены TDS/источником — остаётся в §14;
5. `UNKNOWN` должен оставаться неизвестным и требовать проверки источника, а не автоматически становиться запретом — выполнено на уровне compatibility workflow;
6. явно `FORBIDDEN` может считаться blocker только при наличии подтверждённой source-backed записи — реализовано в domain semantics.

## §17 — Критическое ограничение
Не закрывать §17 до runtime/UI acceptance.

Минимум для закрытия:
1. domain-модель инспекции с измерениями, дефектами, фото-ссылками и source identity — выполнено;
2. сервис создания/валидации/сериализации — выполнено;
3. UI workflow с созданием записи и просмотром сводки — выполнено в `16c3825cb6a913dd36c216e79987c615ce476fae`, но runtime acceptance ещё не выполнен;
4. regression/smoke с `UNKNOWN`, измерением и дефектом — тест добавлен в `eab29520a26b406839bdcff8cba39a3626d827a0`, но пока не запускался;
5. нормативные пределы и приёмочные решения не должны генерироваться без подтверждённого источника/решения инспектора — выполнено на уровне domain/service.

## Восстановленное содержание §23–§32

> Источник восстановления: историческая версия `docs/plan2akz.md` из commit `a7bdbe98be8079cbeb677811a3e881da6572367f` (`docs: extend plan2akz engineering roadmap from 2026-09-10`).
> Восстановлены исходные формулировки roadmap; это не означает выполнения пунктов.

## 23. Pre-Application Check / технологическая готовность — P1

**[НЕ ВЫПОЛНЕНО]**

Развить существующие инженерные фильтры в отдельную проверку готовности к нанесению.

Проверять при наличии данных:
- температура воздуха;
- температура поверхности;
- RH;
- точка росы и запас до неё;
- минимальная/максимальная температура нанесения по слоям;
- межслойная выдержка;
- pot life/induction time для 2К;
- способ нанесения;
- фактический/заданный DFT;
- необходимость разбавления;
- ограничения производителя.

Результат: `Подходит / Не подходит / Недостаточно данных` + конкретная причина.

## 24. Химическая стойкость и среда эксплуатации — P1

**[НЕ ВЫПОЛНЕНО]**

Добавить инженерную модель воздействия среды:
- тип среды;
- химические вещества/класс воздействия;
- концентрация при наличии данных;
- температура воздействия;
- постоянный/периодический контакт;
- погружение/брызги/конденсация;
- механическое воздействие при наличии данных.

Связывать требования среды с материалом/системой только через явные правила с источником. Не делать «универсальную химическую стойкость» по названию смолы.

## 25. Нормативная traceability — P1

**[НЕ ВЫПОЛНЕНО]**

Создать модель `NormativeDocument` / `NormativeRule` или эквивалентную структуру.

Каждое инженерное решение, если оно основано на нормативе, должно уметь показать:
- документ;
- редакцию/версию;
- пункт/раздел;
- применённое правило;
- дату актуальности.

Версии ISO/ГОСТ не должны теряться внутри расчёта.

## 26. Explanation Engine — P1

**[НЕ ВЫПОЛНЕНО]**

Для рекомендации/сравнения добавить объяснение результата человеческим языком:
- почему система прошла/не прошла hard filter;
- какое правило отбора сработало;
- какие данные отсутствуют;
- почему одна система отличается от другой;
- какие ограничения являются worst-case.

Explanation Engine не должен самостоятельно принимать инженерное решение: он объясняет уже рассчитанный результат и его источники.

## 27. Material Data Quality / полнота карточек — P1

**[НЕ ВЫПОЛНЕНО]**

Добавить контроль полноты инженерных данных материала перед использованием в recommendation/compatibility.

Поля/источники для контроля:
- химическая основа/связующее;
- плотность;
- сухой остаток;
- DFT limits;
- температуры нанесения;
- RH;
- точка росы;
- межслойные выдержки;
- pot life/induction для 2К;
- способы нанесения;
- химическая стойкость;
- источник каждого критичного параметра.

Для табличного импорта из `books/Системы 1.xls`, `books/Системы 2.XLSX`, `books/Системы 3.xlsx`, `books/Системы 4.xlsx`:
- сначала определить структуру листов и колонок;
- сопоставлять только явно распознанные поля;
- неизвестные/неоднозначные поля сохранять как `UNKNOWN`;
- проверять дубликаты по нормализованному имени/идентификатору, не создавая повторные карточки;
- хранить provenance: исходный файл, лист, строку/ячейку и хэш источника;
- данные из таблиц не считать TDS/нормативом без отдельной проверки.

## 28. Loss Profile / расход и потери — P1

**[НЕ ВЫПОЛНЕНО]**

Развить `LossProfile` в управляемую инженерную модель потерь:
- тип нанесения;
- геометрия/сложность объекта;
- условия нанесения;
- диапазон потерь;
- источник/обоснование;
- default только при явном отсутствии пользовательского значения.

Не менять базовую формулу расхода без regression и golden cases.

## 29. System Templates / каталог типовых систем — P2

**[НЕ ВЫПОЛНЕНО]**

Создать преемник legacy `CoatingTemplateDialog`: сохранённые типовые системы покрытия с версионированием и возможностью создать из шаблона новый черновик.

Шаблон должен хранить именно инженерную систему слоёв, а не UI-структуру старого калькулятора.

Новые источники `books/Системы 1.xls`, `books/Системы 2.XLSX`, `books/Системы 3.xlsx`, `books/Системы 4.xlsx` считать исходным каталогом вариантов систем и материалов для реализации этого этапа.

Поддержать:
- 2/3/4+ слоёв;
- DFT по слоям;
- разбавление;
- технологические ограничения;
- нормативную/источниковую привязку при наличии;
- несколько вариантов одной системы;
- создание черновика системы из табличной строки;
- предложение отсутствующих материалов к добавлению в БД;
- ручное подтверждение/редактирование перед сохранением;
- provenance каждой импортированной системы и материала.

Ключевое правило: таблицы `Системы 1–4` — источник вариантов и кандидатов на импорт, а не автоматическое подтверждение пригодности системы. TDS и нормативные источники остаются отдельным уровнем верификации.

## 30. Engineering Decision Log — P2

**[НЕ ВЫПОЛНЕНО]**

Хранить объяснимый журнал инженерных решений для расчёта/рекомендации:
- входные условия;
- выбранные hard filters;
- исключённые системы и причины;
- применённые правила;
- источники;
- итоговая система;
- версия приложения/формул/нормативных данных.

Журнал должен быть воспроизводимым и связанным со snapshot расчёта.

## 31. Calculation Scenarios / инженерные сценарии — P2

**[НЕ ВЫПОЛНЕНО]**

Добавить сценарии одного расчёта для быстрого сравнения вариантов условий:
- разные системы;
- разные DFT;
- разные потери;
- разные технологические условия;
- разные нормативные требования.

Сценарий не должен создавать отдельный расчётный движок — используется тот же `CalculationService` и те же модели результата.

В качестве одного из входов сценария после реализации §29 допускается выбор сохранённых вариантов из каталога `Системы 1–4`.

## 32. Inspection / фактический DFT workflow — P2

**[НЕ ВЫПОЛНЕНО]**

Расширить §17 до полноценного inspection workflow:
- зоны контроля;
- измерения DFT;
- проектный/заданный DFT;
- фактический DFT;
- соответствие/несоответствие;
- recoat/repair;
- привязка фото/акта при необходимости.

Инспекция не должна менять исходный расчёт: фактические измерения хранятся как отдельные данные контроля.

## Порядок продолжения
1. GitHub Actions не запускать.
2. Тесты пока не запускать; общий прогон выполнить позже.
3. §10 не считать закрытым без acceptance-доказательства.
4. §9 не расширять складской моделью: коммерческая фасовка остаётся без складского учёта.
5. §11 и §11.1 не закрывать до общего runtime acceptance.
6. §12/§13: добавлять только фактически проверенные sidecar-манифесты с SHA-256 исходного PDF и без придуманных значений, затем подключать только подтверждённые правила.
7. §14 начинать только после появления проверяемого source-backed TDS rule pipeline.
8. §20 продолжать с acceptance/visual smoke и source-linked handoff в инженерные решения; extracted text и табличные данные не превращать автоматически в норматив.
9. §21 не расширять generic chemistry assumptions; applicability подтверждать TDS/источником.
10. §22: выполнить UI regression/acceptance позже; не считать WARNING/UNKNOWN запретом и не добавлять TDS-условия без источника.
11. §17: выполнить runtime/UI acceptance; только после него считать этап закрытым.
12. §18/§19: заполнить acceptance evidence и parity results после общего локального прогона; не считать документы доказательством прохождения сами по себе.
13. §29: использовать `Системы 1–4` как исходные варианты систем и кандидаты на добавление материалов в БД; импорт выполнять через review/staging, с provenance и duplicate protection.
14. После §18/§19 переходить к §23–§32, сохраняя отдельные code/docs commits.
