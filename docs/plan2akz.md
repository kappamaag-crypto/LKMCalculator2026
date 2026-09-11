# План развития LKMCalculator — АКЗ / ОГЗ / инженерный режим

> Живой план для ветки `v3.0-engineering-upgrade`. Статус меняется только по фактическому состоянию кода и тестов.

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
11. GitHub Actions для текущей работы не запускаем из-за лимита; локальные/статические проверки допустимы и должны быть явно обозначены.

## Матрица статуса

| § | Статус | Фактическое состояние / доказательство |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро расчёта сохранено. |
| 2 | ЧАСТИЧНО | Динамический редактор существует; workflow совместимости и визуальный smoke остаются. |
| 3 | ВЫПОЛНЕНО | `AdHocMaterialDialog`: нормализация, duplicate reuse, persistence; regression `42bb7fb`. |
| 4 | ЧАСТИЧНО | ComparisonEngine/View, 2K/многослойность и headless UI smoke `2ad50af`; остаются визуальный smoke и финальная source-backed проверка wording. |
| 5 | ЧАСТИЧНО | Инженерный Excel и regression missing-price `a1e1a0a`; остаются визуальный/печать/PDF-конверсионный smoke. |
| 6 | ЧАСТИЧНО | PDF строится из `SystemCalculationResult`; multilayer/comparison/2K/unknown-price покрыты; cross-export regression `e3ef08d`; остаются визуальный/печать smoke. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants + независимые golden cases 2/3/4/5 layers; успешный CI. |
| 8 | ВЫПОЛНЕНО | 2K учитывается как один смешанный материалный слой; TDS technology rules вынесены в §14. |
| 9 | ЧАСТИЧНО | `PackagingPlanner` считает коммерческую потребность по фасовке: целые упаковки, резерв и опциональную стоимость. Складские остатки, складской учёт, резерв склада и закупочные заказы не входят. |
| 10 | ЧАСТИЧНО | Alembic + SQLite-safe backup/restore; acceptance отложен из-за запрета на Actions/тесты. Необратимые downgrade требуют восстановления backup. |
| 11 | ЧАСТИЧНО | Self-contained immutable material snapshots v5, verified reads и integrity hashing реализованы; acceptance/runtime smoke отложен. |
| 11.1 | ЧАСТИЧНО | Durable notification outbox интегрирован с `calculation_saved`; opt-in worker/trigger, idempotency metadata и env-only SMTP реализованы. SMTP/runtime smoke и тесты отложены. |
| 12 | ЧАСТИЧНО | Normative foundation + source-preserving serializer + History snapshot v7 реализованы. `SystemCalculationResult` типизированно содержит `EngineeringContext`; `SystemCalculator`, `CalculationService` и `CalculationView` принимают/переносят его явно. History умеет сохранять и восстанавливать typed context, включая legacy v6. В UI есть редактор source identity и реестр доступных source-документов с выбором из каталога. Добавлен безопасный loader проверенного sidecar-манифеста: он требует существующий source-файл и SHA-256, не извлекает и не угадывает нормативные значения. Loader умеет загружать явно перечисленные verified sidecars в строгий `NormativeRegistry` с защитой от дубликатов. Фактический набор verified rules/manifest пока не добавлен. Acceptance отложен. |
| 13 | ЧАСТИЧНО | `SurfacePreparation`, `SurfaceProfile`, `SurfaceCondition` + serializer и History snapshot v7 реализованы. `CalculationView` хранит/принимает typed surface context и восстанавливает его из history; legacy object surface сохраняется как fallback. В UI есть редактор подготовки/профиля и их источников. Без источника assessment остаётся `UNKNOWN`. Acceptance отложен. |
| 14 | НЕ ВЫПОЛНЕНО | Полная TDS-backed technological validation. Начинать после появления проверяемого source-backed rule pipeline. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Legacy recommendation hard-filter/score; environment/technology/compatibility/explanation/weights остаются. |
| 17 | НЕ ВЫПОЛНЕНО | Inspection workflow. |
| 18 | НЕ ВЫПОЛНЕНО | Release/regression/smoke/DB backup/docs acceptance. |
| 19 | НЕ ВЫПОЛНЕНО | Legacy parity matrix. |
| 20 | ЧАСТИЧНО | `book_index.py` индексирует source identity/integrity файлов `books/`. `book_content_index.py` извлекает searchable content из PDF и UTF-8 text-like файлов в детерминированные source-linked chunks с path/SHA-256/locator. `BookSearchService` предоставляет lazy rebuild и source-linked search API поверх этого индекса. Извлечённый текст не превращается в нормативные правила. Полноценная UI/DB KB и acceptance остаются. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix есть; applicability к реальной chemistry/TDS остаётся. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | `LayerCompatibilityEngine` подключён к `CalculationService.format_summary()`, поэтому обычный `CalculationView` уже получает source-backed результат проверки соседних слоёв после расчёта. Проверка не блокирует расчёт и `UNKNOWN` не превращается в запрет. Остаётся прямое workflow-подключение `SystemsView`, UI regression и TDS-backed conditions. |
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

### §12 — Versioned normative model foundation
Code commit: `709eadea3be513fb3a2a540dc195ef93956f4b09` — immutable source-backed normative model с версиями, правилами, registry и явным `UNKNOWN`.

### §13 — Structured Sa/St/profile foundation
Code commit: `6d3c86145e99c8c9a653cb1dff9823639c3fef41` — structured surface preparation/profile model без hard-coded нормативных значений.

### §12/§13 — Persistence serialization foundation
Code commit: `4a623ed5bf0b19d34bb57009135f8b96b54cb634` — source-preserving serializer для `NormativeModel` и `SurfaceCondition`.

### §12/§13 — History snapshot integration
Code commit: `7d4d40e6b6985a159b9a998438db32ca79ed4c14` — History snapshot v6 сохраняет structured surface context и нормативную модель только при фактической передаче.

### §12 — Normative workflow propagation
Code commit: `135843fcb40ac57b9db795731e68a1a9b2fa9e8` — переходный этап: `SystemCalculator` принимает `NormativeModel` и переносит его в результат; затем формализован типизированный context.

### §12/§13 — Typed engineering context
Code commit: `70ec88eb28101e3a78f332f9be10303c22a9b320` — `SystemCalculationResult.engineering_context` с immutable `EngineeringContext` и без динамического атрибута `normative_model`.

### §12/§13 — Typed calculator propagation
Code commit: `d31971c5b725da2b2ff351500c70b4d269ac5ceb` — `SystemCalculator` нормализует legacy `normative_model` в typed context и поддерживает явную передачу `EngineeringContext` для обычного и template расчёта.

### §12/§13 — Context serializer round-trip
Code commit: `c63fc757fed36249f25b7eb6384fb6f69bd00547` — добавлен source-preserving round-trip `EngineeringContext` serializer/deserializer.

### §12/§13 — History typed-context persistence/restore
Code commit: `6e112c2621af2adef23b4d72c4025bfdb627543c` — History snapshot v7 хранит типизированный engineering context и добавлен `get_calculation_engineering_context()` с обратной совместимостью для v6.

### §12 — Application service propagation
Code commit: `b545603bef83dfb10b346516f9f19a7b305d8494` — `CalculationService.calculate_system()` и `calculate_from_template()` принимают явный `EngineeringContext` и передают его в domain calculator.

### §12/§13 — CalculationView workflow integration
Code commit: `98d3fe008f420067ee8db8ae30447682d5c273c` — `CalculationView` хранит typed engineering context, передаёт его при расчёте и восстанавливает из snapshot, включая legacy v6 representation.

### §12/§13 — UI source/context editor
Code commit: `4f9175755f8e43100b80f4f43cddf58a3248ef4a` — добавлен отдельный диалог редактирования нормативного source identity, подготовки поверхности и профиля; значения не подменяются нормативными догадками.

### §12/§13 — MainWindow engineering workflow
Code commit: `cd58fa3ee2d24d3a5eeb7d1140aea3d4a231180a` — в главное окно добавлен раздел «Инженерное → Контекст НД и поверхности…», контекст передаётся в `CalculationView` и участвует в расчёте.

### §12 — Engineering source registry
Code commit: `608f84c0501cd57f147c876a23417990fca13ab8` — добавлен реестр доступных repository-resident источников; реестр хранит только идентичность документов и не создаёт нормативных правил автоматически.

### §12/§13 — Source registry UI integration
Code commit: `27d7cff3194564728682bf330a651b31163e0a34` — диалог инженерного контекста подключён к реестру нормативных документов; выбор source-документа заполняет только его идентичность, без генерации нормативных значений.

### §12 — EngineeringContext restoration and status semantics
Code commit: `6db6da2b5a72d9d93a2bbd6ea8a4572c2dc0e916` — восстановлен отсутствующий в текущем дереве `upload/app/domain/engineering_context.py`; `normative_status` больше не объявляет source identity «KNOWN» без хотя бы одного явного known rule.

### §12 — Verified source-backed rule import boundary
Code commit: `f425ab1ed46697807f0c0c1414429f2ac631e872` — добавлен `verified_normative_loader.py`: human-reviewed JSON sidecar принимается только при наличии source-файла, совпадении SHA-256, валидной схеме model/rules и явных значениях для `KNOWN` правил. Loader не извлекает значения из PDF и не делает инженерных предположений.

### §12 — Verified sidecar registry assembly
Code commit: `76f5c6ad5f65ac339a98382eb50d7f21ef200142` — verified loader теперь умеет принимать явно заданный набор sidecar-манифестов и регистрировать проверенные `NormativeModel` в `NormativeRegistry`; дубликаты `model_id:version` отклоняются. Автопоиск манифестов и подстановка нормативных значений не добавлялись. Фактические SHA-256 и rule values по PDF пока не внесены.

### §20 — Repository book source index
Code commit: `1c0fe4e83d4d02c7fd9828547bc7e45a669ffc28` — добавлен детерминированный `book_index.py`: индексирует файлы `books/`, считает SHA-256 и сохраняет source identity/integrity metadata; PDF не интерпретируются и нормативные значения не выводятся автоматически.

### §20 — Source-preserving book content index
Code commit: `5805f111719b5b664d01a447d9e76596d5393cda` — добавлен `book_content_index.py`: PDF и text-like content извлекаются в детерминированные source-linked chunks с path/SHA-256/locator; извлечённый текст предназначен только для поиска и не становится нормативным правилом автоматически.

### §20 — PDF extraction dependency
Code commit: `83f12f8b0eb2d261ac04f19a257e4a91553fc028` — добавлен `pypdf>=5.0.0` в `upload/requirements.txt` для явной поддержки PDF content indexing.

### §20 — Source-linked book search service
Code commit: `2c084a315d27b5bc181ff57177a1cdae6c02dcaa` — добавлен `BookSearchService`: lazy построение контентного индекса и детерминированный API поиска, возвращающий `relative_path`, `locator`, SHA-256 и текст каждого результата. Сервис остаётся reference-search слоем и не создаёт нормативных правил.

### §22 — Calculation workflow integration
Code commit: `2ea726933b859c8e00dd17069be437cb6251a302` — `CalculationService` получил `LayerCompatibilityEngine`; добавлен `compatibility_report()` и source-backed блок совместимости в `format_summary()`. После расчёта `CalculationView` получает статус и сообщения по каждому переходу между соседними слоями. Проверка информационная: `UNKNOWN` не блокирует расчёт и не превращается в запрет. TDS-specific cure/recoat conditions намеренно не выводятся из общих предположений.

## §22 — Критическое ограничение
Не закрывать §22 до фактического подключения `LayerCompatibilityEngine` к пользовательскому workflow расчёта/системы. Наличие standalone engine недостаточно.

Минимум для закрытия:
1. интеграция проверки в `CalculationView` — выполнена через `CalculationService.format_summary()`;
2. интеграция проверки в `SystemsView`/редактор системы — остаётся;
3. UI regression на положительный, отрицательный и `UNKNOWN` сценарии — остаётся;
4. условия `previous_is_cured`, `recoat_elapsed_h`, `surface_prepared` только если они подтверждены TDS/источником — остаётся в §14;
5. `UNKNOWN` должен оставаться неизвестным и требовать проверки источника, а не автоматически становиться запретом — выполнено на уровне compatibility workflow.

## Порядок продолжения
1. GitHub Actions не запускать из-за лимита пользователя.
2. Тесты пока не запускать; общий прогон выполнить позже.
3. §10 не считать закрытым без acceptance-доказательства.
4. §9 не расширять складской моделью: коммерческая фасовка остаётся без складского учёта.
5. §11 и §11.1 не закрывать до общего runtime acceptance.
6. §12/§13: механизм безопасной загрузки verified source-backed rules создан; добавлена сборка явно перечисленного набора sidecar-манифестов в `NormativeRegistry`. Следующий шаг — добавить только фактически проверенные sidecar-манифесты для выбранных документов с SHA-256 исходного PDF и без придуманных значений, затем подключить фактический registry к инженерному workflow.
7. После фактического набора verified rules перейти к §14 TDS-backed technological validation.
8. §20: source/integrity index и source-preserving content/search index созданы. Следующий шаг — интегрировать `BookSearchService` в инженерный workflow/KB с явным source-linked результатом, не превращая извлечённый текст в нормативные правила и сохраняя source identity.
9. §22 вести отдельно: CalculationView workflow integration выполнена, следующий шаг — SystemsView и UI regression; формально не закрывать до полного workflow integration.
10. После каждого code commit — отдельный plan/docs commit с фактическим SHA и текущим статусом.
