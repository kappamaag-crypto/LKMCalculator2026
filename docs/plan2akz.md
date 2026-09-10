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
| 12 | ЧАСТИЧНО | Normative foundation + source-preserving serializer + History snapshot v7 реализованы. `SystemCalculationResult` типизированно содержит `EngineeringContext`; `SystemCalculator`, `CalculationService` и `CalculationView` принимают/переносят его явно. History умеет сохранять и восстанавливать typed context, включая legacy v6. В UI появился явный редактор source identity нормативной базы; реальные source-backed правила по-прежнему не загружаются автоматически. Acceptance отложен. |
| 13 | ЧАСТИЧНО | `SurfacePreparation`, `SurfaceProfile`, `SurfaceCondition` + serializer и History snapshot v7 реализованы. `CalculationView` хранит/принимает typed surface context и восстанавливает его из history; legacy object surface сохраняется как fallback. В UI появился редактор подготовки/профиля и их источников. Без источника assessment остаётся `UNKNOWN`. Acceptance отложен. |
| 14 | НЕ ВЫПОЛНЕНО | Полная TDS-backed technological validation. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Legacy recommendation hard-filter/score; environment/technology/compatibility/explanation/weights остаются. |
| 17 | НЕ ВЫПОЛНЕНО | Inspection workflow. |
| 18 | НЕ ВЫПОЛНЕНО | Release/regression/smoke/DB backup/docs acceptance. |
| 19 | НЕ ВЫПОЛНЕНО | Legacy parity matrix. |
| 20 | НЕ ВЫПОЛНЕНО | Indexed KB из `books/`. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix есть; applicability к реальной chemistry/TDS остаётся. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | `LayerCompatibilityEngine` и tests существуют, но не подключены к `CalculationView`/`SystemsView`; нужны workflow integration, UI regression и TDS-backed conditions. `UNKNOWN` не превращать в запрет. |
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
Code commit: `98d3fe008f420067ee8db8ae30447682d5c2730d` — `CalculationView` хранит typed engineering context, передаёт его при расчёте и восстанавливает из snapshot, включая legacy v6 representation.

### §12/§13 — UI source/context editor
Code commit: `4f9175755f8e43100b80f4f43cddf58a3248ef4a` — добавлен отдельный диалог редактирования нормативного source identity, подготовки поверхности и профиля; значения не подменяются нормативными догадками.

### §12/§13 — MainWindow engineering workflow
Code commit: `cd58fa3ee2d24d3a5eeb7d1140aea3d4a231180a` — в главное окно добавлен раздел «Инженерное → Контекст НД и поверхности…», контекст передаётся в `CalculationView` и участвует в расчёте.

Тесты, runtime smoke и GitHub Actions для этих этапов намеренно не запускались по указанию пользователя. Поэтому §12/§13 остаются `ЧАСТИЧНО`.

## §22 — Критическое ограничение
Не закрывать §22 до фактического подключения `LayerCompatibilityEngine` к пользовательскому workflow расчёта/системы. Наличие standalone engine/tests недостаточно.

Минимум для закрытия:
1. интеграция проверки в `CalculationView`;
2. интеграция проверки в `SystemsView`/редактор системы;
3. UI regression на положительный, отрицательный и `UNKNOWN` сценарии;
4. условия `previous_is_cured`, `recoat_elapsed_h`, `surface_prepared` только если они подтверждены TDS/источником;
5. `UNKNOWN` должен оставаться неизвестным и требовать проверки источника, а не автоматически становиться запретом.

## Порядок продолжения
1. GitHub Actions не запускать из-за лимита пользователя.
2. Тесты пока не запускать; общий прогон выполнить позже.
3. §10 не считать закрытым без acceptance-доказательства.
4. §9 не расширять складской моделью: коммерческая фасовка остаётся без складского учёта.
5. §11 и §11.1 не закрывать до общего runtime acceptance.
6. §12/§13: следующий шаг — дать пользователю безопасный выбор/реестр конкретных source-backed моделей и правил (без генерации нормативных значений); затем переходить к §14, не выдумывая нормативные значения.
7. §22 вести отдельно и не закрывать формально до полного workflow integration.
8. После каждого code commit — отдельный plan/docs commit с фактическим SHA и текущим статусом.

## Контроль
Новые GitHub Actions runs не запускаются. Тесты/runtime smoke намеренно отложены по указанию пользователя.
