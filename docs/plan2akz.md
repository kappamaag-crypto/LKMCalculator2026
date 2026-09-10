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
| 6 | ЧАСТИЧНО | PDF строится из `SystemCalculationResult`; multilayer/comparison/2K/unknown-price покрыты; cross-export regression `e3ef08d`; остаются визуальный/печать smoke. CI для `e3ef08d` был queued и не является доказательством успеха до завершения run. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants + независимые golden cases 2/3/4/5 layers; успешный CI. |
| 8 | ВЫПОЛНЕНО | 2K учитывается как один смешанный материалный слой; TDS technology rules вынесены в §14. |
| 9 | ЧАСТИЧНО | `PackagingPlanner` считает коммерческую потребность по фасовке: целые упаковки, резерв и опциональную стоимость; regression `26897211`. Складские остатки, складской учёт, резерв склада и закупочные заказы в проект не входят. Полный коммерческий workflow/UI ещё не реализован. |
| 10 | ЧАСТИЧНО | Alembic присутствует. Добавлены SQLite-safe backup/restore helpers `de1fd6f` и regression/migration idempotency `f8adeff`; acceptance CI не используем из-за исчерпанного Actions-лимита. Для миграций с необратимым `downgrade` (например, `004_nullable_calculation_inputs`) rollback должен выполняться восстановлением предмиграционного backup, а не возвратом данных к вымышленным значениям. |
| 11 | ЧАСТИЧНО | Immutable snapshots усилены: `HistoryService` формирует self-contained material payload, `snapshot_version` поднят до 5; `snapshot_service` восстанавливает современные snapshots без зависимости от mutable catalog, с fallback только для legacy-полей. `HistoryView` открывает snapshot через `HistoryService.get_calculation_snapshot`. Code commits `e63b4ba`, `0104553c`, `012bff6`, `a75311d`, `3a799e2`, `30f8b20`; regression `3b8ffab`, `4b232ece`. Acceptance/runtime smoke намеренно отложен до общего прогона; Actions не используются. |
| 11.1 | ЧАСТИЧНО | Добавлен durable notification outbox: Alembic `005_notification_outbox`, уникальный `idempotency_key`, статусы `pending/sending/retry/sent/failed`, счётчик попыток, `next_attempt_at`, `last_error`, `sent_at`. Добавлен `NotificationService` с deterministic idempotency key, повторным enqueue без дублей, exponential backoff и ограничением `max_attempts`. SMTP-credentials читаются только из environment и не сохраняются в БД. Code commits `2685f1f`, `dd7d600`, `138145f`. Реальный SMTP smoke и runtime проверки пока намеренно не выполнялись; §11.1 не закрывать до общего прогона. |
| 12 | НЕ ВЫПОЛНЕНО | Versioned normative model. |
| 13 | НЕ ВЫПОЛНЕНО | Structured Sa/St/profile model. |
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

### §3 — Ad hoc materials
Code commit: `42bb7fb282774e6f2c1691557ceba86d77795d21`.

### §4 — Comparison UI regression
Code commit: `2ad50af7c4de6b0b5ddbb0ef5113dbb023de2d8f`.

### §5 — Missing-price regression
Code commit: `a1e1a0a1d7fd34c6fee3537dec39e98f13f6281c`.

### §6 — Cross-export regression
Code commit: `e3ef08d3f6eae299ffe482a0dd8e557736334b2b`.

### §9 — Commercial packaging foundation
Code commit: `8e37341cf2be0000a8c346d417dc0b22268f19ae` — packaging domain очищен от складских остатков и складской логики.

Regression commit: `268972115c31050797a08479110c5c69747d5932` — tests aligned with the no-inventory model.

`PackagingPlanner` работает только с уже рассчитанной потребностью: фасовка, целые упаковки, коммерческий резерв и явно переданная цена. Складские остатки/резервы/заказы не моделируются.

### §10 — Database safety foundation
Code commit: `de1fd6f9a863ecd532bef556d8a342311fd1dca8` — `backup.py` с SQLite online backup/restore.

Regression commit: `f8adeff48d6985be9cea833e4bfd0461530805bf` — backup/restore snapshot test, same-path guard и Alembic upgrade idempotency/head test.

CI run `34453753830` для `f8adeff` ранее был `queued`. По запросу пользователя новые GitHub Actions runs не запускаются; поэтому §10 не переводится в `ВЫПОЛНЕНО` без доступного локального acceptance-доказательства.

### §11 — Immutable history snapshots
Code commit: `e63b4baaa7912cf92e9bd8b615edb2731cf1d44a` — canonical/tamper-evident snapshot helpers.

Code commit: `0104553c219844dfe8c80e4c485b5a514d727cd8` — `HistoryService` seals calculation/comparison snapshots and exposes verified snapshot reads.

Regression commit: `3b8ffab399e7665c4f59cb6bee9a8fc076c2bf66` — deterministic hash, tamper rejection and explicit legacy-unsealed behavior.

Code commit: `012bff67f013601be715ec8ea5dedc284f28e9d6` — individual calculation-layer snapshots are now sealed as independent immutable records.

Regression commit: `4b232ecef956811a554568032a11fae9f1f81f5d` — nested/layer snapshot integrity regression, including detection of changed catalog-like values.

Code commit: `a75311d46a5f75364d139965fb7a231c503e99bd` — `HistoryView` загружает только verified snapshot через `HistoryService`, без прямого `json.loads` из ORM.

Code commit: `3a799e2a49fcfa7af92c1ab5a8b3103043f76b19` — material payload snapshot v5 стал self-contained: сохраняются все поля `Material`, включая инженерные/технологические ограничения и документы.

Code commit: `30f8b20aa5b6ec4e371792413829ae2b9eea05fb` — `snapshot_service` восстанавливает современные material snapshots из snapshot-данных; catalog fallback оставлен только для отсутствующих legacy-полей.

### §11.1 — Notification outbox foundation
Code commit: `2685f1f27c654d3fe79b3746f108984cd35dba24` — Alembic migration `005_notification_outbox` с durable queue, статусами retry lifecycle и уникальным idempotency key.

Code commit: `dd7d600885c6c911a2760eb74daee90008d46796` — ORM adapter `NotificationOutboxORM`; SMTP credentials отсутствуют в persistent model.

Code commit: `138145f1708f3c587576ba24aa1984b03edea57a` — `NotificationService`: deterministic idempotency, durable enqueue, bounded retry/backoff и SMTP adapter с credentials только из environment.

Реальный SMTP/runtime smoke и тесты сейчас не запускаются по указанию пользователя; поэтому §11.1 остаётся `ЧАСТИЧНО`.

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
2. §10 не считать закрытым без acceptance-доказательства; существующие backup/restore и migration tests сохранять.
3. §9 не расширять складской моделью: коммерческая фасовка остаётся без складского учёта.
4. §11 остаётся `ЧАСТИЧНО` до общего runtime acceptance; написанный код не считать заменой прогона.
5. Текущий рабочий этап — §11.1: notification outbox, идемпотентность, retry и безопасные SMTP secrets реализованы кодово, но runtime/SMTP acceptance отложен.
6. После acceptance §11.1 перейти к §12, затем далее по матрице.
7. §22 вести отдельно и не закрывать формально до полного workflow integration.
8. После каждого code commit — отдельный plan/docs commit с фактическим SHA и текущим статусом.

## CI / контрольные точки
- `34439245472`
- `34439280625`
- `34440681323`
- `34437813196`
- `34451490167` — commit `e3ef08d3`, был queued.
- `34453199922` — commit `42bc3b6`, queued на момент фиксации.
- `34453210684` — commit `1f9cbd6`, queued на момент фиксации.
- `34453753830` — commit `f8adeff`, queued; новые Actions runs по текущей работе не запускаются.

## Последняя проверка
`2026-09-10` — GitHub Actions не запускаются по просьбе пользователя из-за исчерпания лимита. Тесты и runtime smoke намеренно не запускались. §11 остаётся `ЧАСТИЧНО`; §11.1 получил кодовую основу durable outbox/SMTP/retry/idempotency, но также остаётся `ЧАСТИЧНО` до общего прогона.

## Следующий рабочий фокус
§11.1: довести notification workflow до интеграционного уровня без запуска Actions — привязать enqueue к реальному событию приложения, определить безопасный lifecycle worker/trigger и затем после общего прогона закрыть acceptance. После этого перейти к §12.