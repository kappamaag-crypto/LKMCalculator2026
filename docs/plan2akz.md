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
| 3 | ВЫПОЛНЕНО | `AdHocMaterialDialog`: нормализация, duplicate reuse, persistence; regression `42bb7fb`. |
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
| 17 | ЧАСТИЧНО | Добавлены typed `InspectionRecord`, измерения и дефекты, `InspectionService` для создания/валидации/сводки/serialization и regression cases. UI-вкладка «Инспекция» и пункт инженерного меню подключены code commit `16c3825cb6a913dd36c216e79987c615ce476fae`. Приёмочный статус по умолчанию `UNKNOWN`; нормативные критерии не выводятся автоматически. Runtime/UI acceptance ещё не выполнены. |
| 18 | НЕ ВЫПОЛНЕНО | Release/regression/smoke/DB backup/docs acceptance. |
| 19 | НЕ ВЫПОЛНЕНО | Legacy parity matrix. |
| 20 | ЧАСТИЧНО | `book_index.py` индексирует source identity/integrity файлов `books/`; `book_content_index.py` извлекает searchable content из PDF и UTF-8 text-like файлов в source-linked chunks с path/SHA-256/locator; `BookSearchService` имеет DB-backed persistence/search; `BookSearchView` подключён отдельной вкладкой и меню, показывает source/locator/SHA-256, а выбранный источник можно передать в инженерный контекст как `UNKNOWN` source identity без создания нормативного значения. Остаются acceptance/visual smoke и более глубокая интеграция KB с инженерными решениями. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix есть; applicability к реальной chemistry/TDS остаётся. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | `LayerCompatibilityEngine` подключён к `CalculationService.format_summary()` и напрямую к `SystemsView`: редактор показывает source-backed статус и переходы, обновляя их при изменении слоёв. `RecommendationEngine` также переносит compatibility warnings/limitations без изменения ranking. Семантика уточнена: только явно запрещённый source-backed переход является blocker; `WARNING` и `UNKNOWN` требуют инженерной проверки и не превращаются в автоматический запрет. Остаются UI regression/acceptance и TDS-backed conditions. |
| 23 | НЕ ВЫПОЛНЕНО | — |
| 24 | НЕ ВЫПОЛНЕНО | — |
| 25 | НЕ ВЫПОЛНЕНО | — |
| 26 | НЕ ВЫПОЛНЕНО | — |
| 27 | НЕ ВЫПОЛНЕНО | — |
| 28 | НЕ ВЫПОЛНЕНО | — |
| 29 | НЕ ВЫПОЛНЕНО | — |
| 30 | НЕ ВЫПОЛНЕНО | — |
| 31 | НЕ ВЫПОЛНЕНО | — |
| 32 | НЕ ВЫПОЛНЕНО | — |

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

## Порядок продолжения
1. GitHub Actions не запускать.
2. Тесты пока не запускать; общий прогон выполнить позже.
3. §10 не считать закрытым без acceptance-доказательства.
4. §9 не расширять складской моделью: коммерческая фасовка остаётся без складского учёта.
5. §11 и §11.1 не закрывать до общего runtime acceptance.
6. §12/§13: добавлять только фактически проверенные sidecar-манифесты с SHA-256 исходного PDF и без придуманных значений, затем подключать только подтверждённые правила.
7. §14 начинать только после появления проверяемого source-backed TDS rule pipeline.
8. §20 продолжать с acceptance/visual smoke и source-linked handoff в инженерные решения; extracted text не превращать автоматически в норматив.
9. §21 не расширять generic chemistry assumptions; applicability подтверждать TDS/источником.
10. §22: выполнить UI regression/acceptance позже; не считать WARNING/UNKNOWN запретом и не добавлять TDS-условия без источника.
11. §17: выполнить runtime/UI acceptance; только после него считать этап закрытым.
12. После §17 переходить к §18 → §19 и оставшимся §23–§32, сохраняя отдельные code/docs commits.
