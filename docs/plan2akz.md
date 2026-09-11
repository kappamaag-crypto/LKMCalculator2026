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
8. После code commit — отдельный docs/plan commit.
9. `ВЫПОЛНЕНО` ставится только при реализации и проверочном доказательстве.
10. Отсутствующие/непроверенные данные = `UNKNOWN`; запреты и разрешения не выдумывать.
11. GitHub Actions не запускать. Тесты пока не запускать; общий прогон выполнить позже.
12. Репозиторий `kappamaag-crypto/SPKEFFA` используется только как внешний read-only источник TDS. Его не изменять.

## Матрица статуса

| § | Статус | Фактическое состояние / следующий шаг |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро расчёта сохранено. |
| 2 | ЧАСТИЧНО | Динамический редактор есть; остаются совместимость workflow и визуальный smoke. |
| 3 | ВЫПОЛНЕНО | `AdHocMaterialDialog`: нормализация, duplicate reuse, persistence; regression `42bb7fb`. |
| 4 | ЧАСТИЧНО | ComparisonEngine/View, 2K и многослойность реализованы; остаются визуальный smoke и source-backed wording check. |
| 5 | ЧАСТИЧНО | Инженерный Excel и missing-price regression есть; остаётся визуальная/печатаемая проверка. |
| 6 | ЧАСТИЧНО | PDF строится из `SystemCalculationResult`; multilayer/2K/unknown-price и cross-export regression есть; остаётся визуальный/печать smoke. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants и golden cases 2/3/4/5 layers. |
| 8 | ВЫПОЛНЕНО | 2K считается одним смешанным материалным слоем; TDS technology rules вынесены в §14. |
| 9 | ЧАСТИЧНО | `PackagingPlanner`: целые упаковки, резерв, опциональная стоимость; складского учёта нет и не добавлять. |
| 10 | ЧАСТИЧНО | Alembic + SQLite-safe backup/restore; acceptance ещё не выполнен. |
| 11 | ЧАСТИЧНО | Immutable material snapshots v5, verified reads, integrity hashing; runtime acceptance ещё не выполнен. |
| 11.1 | ЧАСТИЧНО | Durable notification outbox + opt-in worker/trigger + idempotency + env-only SMTP; runtime/SMTP acceptance ещё не выполнен. |
| 12 | ЧАСТИЧНО | Engineering context, source identity, History v7 и verified sidecar loader с SHA-256 реализованы; фактический verified rules/manifest ещё не добавлен. |
| 13 | ЧАСТИЧНО | `SurfacePreparation/Profile/Condition`, serializer, History и UI реализованы; без источника остаётся `UNKNOWN`. Acceptance ещё не выполнен. |
| 14 | НЕ ВЫПОЛНЕНО | TDS-backed technological validation. Начать с проверенного rule pipeline и TDS из `SPKEFFA` read-only. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Legacy ranking сохранён; compatibility warnings/limitations передаются в recommendations. Полная environment/technology/weight scoring остаётся. |
| 17 | ЧАСТИЧНО | Inspection domain/service/UI реализованы; runtime/UI acceptance ещё не выполнен. |
| 18 | ЧАСТИЧНО | Release acceptance checklist есть; evidence пока `PENDING`. |
| 19 | ЧАСТИЧНО | Legacy parity matrix есть; строки пока `PENDING`. |
| 20 | ЧАСТИЧНО | KB индексирует source identity/SHA-256 и searchable content. `Системы 1.xls`, `Системы 2.XLSX`, `Системы 3.xlsx`, `Системы 4.xlsx` индексируются; staging importer и Review UI добавлены. БД напрямую не изменяется. Остаются фактическое сопоставление всех строк, UI acceptance и интеграция подтверждённых данных в templates. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix есть. Таблицы «Системы 1–4» могут давать варианты систем, но не заменяют TDS/норматив. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | `LayerCompatibilityEngine` интегрирован в calculation/systems/recommendation workflow. `WARNING`/`UNKNOWN` не являются автоматическим запретом. Остаются UI acceptance и реальные TDS-backed conditions. |
| 23 | НЕ ВЫПОЛНЕНО | Pre-Application Check: климат, RH, dew point, температуры, recoat, 2K pot life/induction, application, DFT, thinner и ограничения производителя. |
| 24 | НЕ ВЫПОЛНЕНО | Химическая стойкость и среда эксплуатации только через явные source-backed rules. |
| 25 | НЕ ВЫПОЛНЕНО | Полная normative traceability: документ, версия, пункт, правило, дата актуальности. |
| 26 | НЕ ВЫПОЛНЕНО | Explanation Engine для объяснения ranking/filter/ограничений и отсутствующих данных. |
| 27 | ЧАСТИЧНО | Material Data Quality. Staging уже показывает candidate materials, duplicate normalization, provenance и статус совпадения с БД. Следующий шаг — подтверждение сопоставления и controlled creation неполных карточек без автозаполнения. |
| 28 | НЕ ВЫПОЛНЕНО | Управляемый `LossProfile`: способ нанесения, геометрия, условия, диапазон, источник. |
| 29 | ЧАСТИЧНО | `Системы 1–4` закреплены как исходный каталог вариантов систем и кандидатов материалов. Staging importer + Review UI реализованы; следующий шаг — System Templates с draft/review/save, 2/3/4+ слоями и provenance. |
| 30 | НЕ ВЫПОЛНЕНО | Engineering Decision Log, связанный со snapshot расчёта. |
| 31 | НЕ ВЫПОЛНЕНО | Calculation Scenarios на едином `CalculationService`; варианты из каталога `Системы 1–4` могут стать входом сценариев. |
| 32 | НЕ ВЫПОЛНЕНО | Полный inspection/DFT workflow: зоны, проектный/фактический DFT, acceptance, repair/recoat, фото/акты. |

## Новый этап — табличный каталог систем и материалов

Файлы в `books/`:
- `Системы 1.xls`
- `Системы 2.XLSX`
- `Системы 3.xlsx`
- `Системы 4.xlsx`

Назначение этих файлов:
1. исходные варианты систем покрытия;
2. источник названий/идентификаторов материалов для формирования кандидатов в БД;
3. исходные данные для будущих System Templates и Calculation Scenarios.

Ограничения:
- исходные таблицы не считаются TDS и нормативом;
- данные таблиц не подтверждают автоматически пригодность системы;
- неизвестные/неоднозначные поля = `UNKNOWN`;
- импорт сначала идёт в staging/review;
- сохранение в БД выполняется только после ручного подтверждения/сопоставления;
- для каждой строки сохраняются файл, лист, строка и SHA-256 источника;
- дубликаты материалов определяются по нормализованному имени до записи в БД;
- TDS остаётся отдельным уровнем верификации.

## Реализованные code stages — KB/catalogue ingestion

### `book_content_index.py`
Commit: `047839b0df403f8ae552394110408b15d219a8c6`

Добавлена индексация строк XLS/XLSX-family с locator вида `sheet:<лист>!row:<номер>`. Для legacy `.xls` содержимое индексируется отдельным reader-путём, а source identity остаётся общей с `book_index.py`.

### `system_catalog_importer.py`
Commit: `d7fa8f5af2b160da8153fe0bf6d93cbfcb527aae`

Добавлен review-first staging importer:
- `SystemRowCandidate` — строка каталога системы;
- `MaterialCandidate` — кандидат материала;
- provenance: файл/лист/строка/SHA-256;
- распознавание колонок по явным заголовкам;
- duplicate normalization;
- отсутствует запись в Material/System DB.

### Зависимость для legacy XLS
Commit: `ff1142c35d09c8b10d3aa708a06cb5576de38563`

Добавлен `xlrd>=2.0.1`. `openpyxl` остаётся reader для XLSX-family.

### `system_catalog_review_view.py`
Commit: `43257fbbbff67fb206b164c5b64baaa0ee347748`

Добавлено отдельное Review/Staging окно:
- список импортированных строк с file/sheet/row/SHA-256;
- отображение полей строки и `UNKNOWN`, если система/обозначение не распознаны;
- список уникальных кандидатов материалов;
- сопоставление с существующей БД по нормализованному display name/material name;
- различение `НЕ НАЙДЕНО` и `НЕОДНОЗНАЧНО`;
- никаких автоматических INSERT/UPDATE в Material/System DB;
- явное предупреждение, что таблица не является TDS.

## §20/§27/§29 — следующий шаг

1. Подтвердить фактическую структуру каждой таблицы/листа при локальном чтении; не считать первую строку заголовком без подтверждения структуры.
2. Для каждого кандидата показывать существующую карточку БД, если найдено однозначное совпадение.
3. Для отсутствующего материала подготовить controlled creation неполной карточки только после ручного подтверждения; отсутствующие поля не заполнять догадкой.
4. Для неоднозначного совпадения требовать ручного выбора, не выбирать автоматически.
5. После review реализовать System Template draft: система → порядок слоёв → материалы → DFT → provenance.
6. Сохранение Template выполнять отдельным явным действием пользователя.
7. После создания Template подключить его к Calculation Scenarios; не создавать второй расчётный движок.
8. TDS-поля заполнять только из проверенных документов; `SPKEFFA` читать только в режиме источника и не изменять.

## §12/§14 — TDS boundary

TDS из `kappamaag-crypto/SPKEFFA` является внешним read-only источником. Репозиторий `SPKEFFA` не изменять.

Для нормативных/технологических правил:
- сначала получить идентичность документа;
- вычислить/зафиксировать SHA-256 исходного PDF;
- правило должно иметь явный source identity и locator;
- только явно подтверждённые значения переводятся в `KNOWN`;
- отсутствующие параметры остаются `UNKNOWN`;
- extracted PDF text сам по себе не становится нормативным правилом.

## §22 — критическое ограничение

Не закрывать §22 до пользовательского acceptance.

`FORBIDDEN` может блокировать только при подтверждённой source-backed записи. `WARNING` и `UNKNOWN` требуют инженерной проверки.

## §17 — критическое ограничение

Не закрывать §17 до runtime/UI acceptance. Инспекция не должна изменять исходный расчёт; фактические измерения хранятся отдельно.

## §18/§19 — acceptance

Не считать checklist/parity matrix доказательством прохождения. Evidence заполняется после локального общего прогона и пользовательского acceptance.

## Порядок продолжения
1. GitHub Actions не запускать.
2. Тесты пока не запускать.
3. Продолжить §20/§27/§29: review сопоставления материалов → controlled creation → System Templates.
4. Параллельно подготовить §14 на основании проверенных TDS из `SPKEFFA`, без изменений в `SPKEFFA`.
5. После source-backed правил развивать §23/§24/§25/§26.
6. Не закрывать частичные пункты без acceptance-доказательства.
7. Каждый существенный code stage фиксировать отдельным commit, затем отдельным docs/plan commit.
