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
| 20 | ЧАСТИЧНО | KB индексирует source identity/SHA-256 и searchable content. `Системы 1.xls`, `Системы 2.XLSX`, `Системы 3.xlsx`, `Системы 4.xlsx` индексируются; staging importer, Review UI и отдельная вкладка `Каталог систем` добавлены. Draft editor с ручным выбором материала добавлен; остаются controlled creation, UI acceptance и фактическое сопоставление всех строк. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix есть. Таблицы «Системы 1–4» могут давать варианты систем, но не заменяют TDS/норматив. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | `LayerCompatibilityEngine` интегрирован в calculation/systems/recommendation workflow. `WARNING`/`UNKNOWN` не являются автоматическим запретом. Остаются UI acceptance и реальные TDS-backed conditions. |
| 23 | НЕ ВЫПОЛНЕНО | Pre-Application Check: климат, RH, dew point, температуры, recoat, 2K pot life/induction, application, DFT, thinner и ограничения производителя. |
| 24 | НЕ ВЫПОЛНЕНО | Химическая стойкость и среда эксплуатации только через явные source-backed rules. |
| 25 | НЕ ВЫПОЛНЕНО | Полная normative traceability: документ, версия, пункт, правило, дата актуальности. |
| 26 | НЕ ВЫПОЛНЕНО | Explanation Engine для объяснения ranking/filter/ограничений и отсутствующих данных. |
| 27 | ЧАСТИЧНО | Material Data Quality. Staging показывает candidate materials, duplicate normalization, provenance и статус совпадения с БД. System Template builder, отдельный persistence boundary и draft editor с ручным выбором существующего Material добавлены; controlled creation неполных карточек остаётся. |
| 28 | НЕ ВЫПОЛНЕНО | Управляемый `LossProfile`: способ нанесения, геометрия, условия, диапазон, источник. |
| 29 | ЧАСТИЧНО | `Системы 1–4` закреплены как исходный каталог вариантов систем и кандидатов материалов. Staging importer + Review UI + draft System Template model/service + DB persistence schema/repository/service + UI editor с явным CONFIRM реализованы. Подключение CONFIRM→persistence и Calculation Scenarios остаётся. |
| 30 | НЕ ВЫПОЛНЕНО | Engineering Decision Log, связанный со snapshot расчёта. |
| 31 | НЕ ВЫПОЛНЕНО | Calculation Scenarios на едином `CalculationService`; варианты из каталога `Системы 1–4` могут стать входом сценариев. |
| 32 | НЕ ВЫПОЛНЕНО | Полный inspection/DFT workflow: зоны, проектный/фактический DFT, acceptance, repair/recoat, фото/акты. |

## Табличный каталог систем и материалов

Файлы в `books/`:
- `Системы 1.xls`
- `Системы 2.XLSX`
- `Системы 3.xlsx`
- `Системы 4.xlsx`

Назначение: исходные варианты систем покрытия, названия/идентификаторы материалов и будущие входы System Templates / Calculation Scenarios.

Ограничения: таблицы не являются TDS/нормативом; не подтверждают автоматически пригодность; неизвестное/неоднозначное = `UNKNOWN`; импорт и review выполняются до записи; сохраняются файл/лист/строка/SHA-256; дубликаты нормализуются; TDS остаётся отдельным уровнем верификации.

## Реализованные code stages — KB/catalogue ingestion

### `book_content_index.py`
Commit: `047839b0df403f8ae552394110408b15d219a8c6`

Индексация XLS/XLSX-family с locator `sheet:<лист>!row:<номер>`. Legacy `.xls` читается через отдельный reader-путь.

### `system_catalog_importer.py`
Commit: `d7fa8f5af2b160da8153fe0bf6d93cbfcb527aae`

Review-first staging importer с `SystemRowCandidate` / `MaterialCandidate`, provenance file/sheet/row/SHA-256, распознаванием явных заголовков и duplicate normalization. Записи в Material/System DB нет.

### Зависимость для legacy XLS
Commit: `ff1142c35d09c8b10d3aa708a06cb5576de38563`

Добавлен `xlrd>=2.0.1`; `openpyxl` остаётся reader для XLSX-family.

### `system_catalog_review_view.py`
Commit: `43257fbbbff67fb206b164c5b64baaa0ee347748`

Добавлен Review/Staging UI: строки источника, file/sheet/row/SHA-256, поля строки, кандидаты материалов, совпадения с БД, состояния `НЕ НАЙДЕНО`/`НЕОДНОЗНАЧНО`, детали строки. Автоматических INSERT/UPDATE нет.

### `system_template.py`
Commit: `d01b0244d46a84e321517a00fe88ed22c3d22187`

Добавлен immutable draft-модель `SystemTemplateDraft` и `TemplateLayer`. Поддержаны статусы `DRAFT`/`REVIEW`/`CONFIRMED`, последовательные слои, DFT-поля, provenance, признаки `has_unknown_materials` и `provenance_complete`. Модель не выполняет persistence.

### `system_template_service.py`
Commit: `5d610e30669d7842598b74ced9049ce433827af9`

Добавлен `SystemTemplateService`: построение draft из `SystemRowCandidate`, однозначное сопоставление с Material DB, `material_id=None` при отсутствии/неоднозначности, сохранение source provenance и проверка `can_confirm()`. TDS applicability не считается подтверждённой автоматически.

### `system_template_models.py`
Commit: `127486c04e6a4a06d92d429c943a188ea7fb1eb1`

Добавлены отдельные ORM-таблицы `system_templates` и `system_template_layers`. Хранят статус, material_id, DFT и source provenance; слой требует существующий Material, поэтому неизвестные/неподтверждённые материалы не попадают в confirmed persistence.

### `system_template_repository.py`
Commit: `b180e757c688eee8ce7e2f9ff083bc524c218108`

Добавлен repository boundary: `add_confirmed()`, поиск по source provenance, чтение и преобразование обратно в draft. Persistence не создаёт Material и не делает автоматический upsert каталога.

### `007_system_templates.py`
Commit: `75b394567d64bbc33f1f8871e503c5f79c46c6b6`

Добавлена Alembic-схема для confirmed System Templates и слоёв с FK на `materials` и уникальностью source provenance.

### `engine.py`
Commit: `cb2d6cc7afe2e6a45ee780be4dd7888eea8dbcb5`

ORM System Template регистрируется до `Base.metadata.create_all()`, поэтому новая схема видима обычному SQLite runtime.

### `system_template_persistence_service.py`
Commit: `da6d542c2a3c1557401ccfcf699b2bdcb42a9e56`

Явная граница `save_confirmed()`: принимает только `CONFIRMED`, требует `tds_verified=KNOWN`, полной provenance и однозначных material_id; при этом не создаёт и не изменяет Material.

### `main_window.py`
Commit: `c960d9ea6e52f74f46b10a91193c31adbcb6f83b`

`SystemCatalogReviewView` подключён отдельной вкладкой `Каталог систем` и пунктом меню `Инженерное → Каталог систем 1–4…`. При изменении Material DB review view обновляет свои сопоставления.

### `system_template_editor_view.py`
Commit: `845be44fdbbd6417112cb89e9804b758894e1a3d`

Добавлен отдельный UI редактора `SystemTemplateDraft`: редактирование имени/описания, просмотр слоёв и DFT, ручной выбор существующего Material, отображение source provenance и `TDS verified`, блокировка `CONFIRM` до прохождения `SystemTemplateService.can_confirm()`. Редактор только эмитит подтверждённый draft; запись в БД должна выполняться отдельной persistence boundary.

## §20/§27/§29 — следующий шаг

1. Подтвердить фактическую структуру каждой таблицы/листа локальным чтением; не считать первую строку заголовком без подтверждения.
2. Для каждого кандидата показывать существующую карточку БД при однозначном совпадении.
3. Для отсутствующего материала — controlled creation неполной карточки только после ручного подтверждения; неизвестные поля не заполнять.
4. Для неоднозначного совпадения требовать ручного выбора.
5. UI редактирования draft реализован: имя системы, слои, материал, DFT и provenance.
6. Подтверждение draft является отдельным явным действием пользователя.
7. Передавать подтверждённый draft в `SystemTemplatePersistenceService`; persistence уже защищён от UNKNOWN material/provenance/TDS.
8. После сохранения Template подключить его к Calculation Scenarios; не создавать второй расчётный движок.

## TDS verification boundary — §12/§14/§25

`SPKEFFA` (`kappamaag-crypto/SPKEFFA`) является read-only источником TDS. PDF/страницы каталога могут быть извлечены для подготовки evidence, но извлечённый текст сам по себе не считается verified normative/technology rule.

Для `KNOWN` требуется отдельная запись документа и правила с явным source identity, применимостью и SHA-256. Git blob SHA-1 не заменяет SHA-256 бинарного PDF. Пока фактические SHA-256 бинарных TDS и rule-by-rule verification не введены, соответствующие технологические ограничения остаются `UNKNOWN`.
