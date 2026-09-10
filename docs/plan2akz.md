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
| 12 | ЧАСТИЧНО | Добавлен immutable versioned normative foundation: `NormativeSource`, `NormativeRule`, `NormativeModel`, `NormativeRegistry`. Известные правила требуют source metadata; отсутствующие правила возвращаются как `UNKNOWN`. Code commit `709eadea`. Нормативные значения и конкретные стандарты намеренно не выдумывались; persistence/integration/regression ещё не выполнены. |
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

### §11.1 — Notification outbox foundation and application integration
Code commits: `2685f1f`, `dd7d600`, `138145f`, `9d10e914`, `4fdec2dd`, `fbe980e`, `baee2aa`.

Реальный SMTP/runtime smoke и тесты не запускаются по указанию пользователя; §11.1 остаётся `ЧАСТИЧНО`.

### §12 — Versioned normative model foundation
Code commit: `709eadea3be513fb3a2a540dc195ef93956f4b09` — добавлен immutable source-backed normative model с версиями, правилами, registry и явным `UNKNOWN`.

Этот commit не закрывает §12: пока нет persistence, интеграции с расчётным snapshot/result и acceptance-прогона.

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
6. Текущий рабочий этап — §12: довести versioned normative model до persistence/integration, затем перейти к §13.
7. §22 вести отдельно и не закрывать формально до полного workflow integration.
8. После каждого code commit — отдельный plan/docs commit с фактическим SHA и текущим статусом.

## Контроль
Новые GitHub Actions runs не запускаются. Тесты/runtime smoke намеренно отложены по указанию пользователя.
