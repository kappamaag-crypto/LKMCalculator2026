# План развития LKMCalculator — АКЗ / ОГЗ / инженерный режим

> Живой план для ветки `v3.0-engineering-upgrade`. Статус меняется только по фактическому состоянию кода и тестов.

## Правила
1. Не ломать существующий расчёт.
2. Инженерная логика находится в domain/service, а не в UI.
3. Excel не является вторым расчётным движком.
4. PDF и Excel получают данные из одного `CalculationResult` / `SystemCalculationResult`.
5. Инженерные и складские/закупочные данные не смешивать без явного назначения.
6. Существенный этап должен иметь regression/smoke-проверку.
7. Каждый существенный этап — отдельный code commit.
8. После code commit — отдельный commit с фиксацией результата в этом плане.
9. `ВЫПОЛНЕНО` ставится только при наличии реализации и тестового/CI или явного smoke-доказательства.
10. При отсутствии исходных данных использовать `UNKNOWN`, не придумывать запрет/разрешение.

## Матрица статуса

| § | Статус | Фактическое состояние / доказательство |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро расчёта сохранено. |
| 2 | ЧАСТИЧНО | Динамический редактор существует; workflow совместимости и визуальный smoke остаются. |
| 3 | ВЫПОЛНЕНО | `AdHocMaterialDialog`: нормализация, duplicate reuse, persistence; regression `42bb7fb`. |
| 4 | ЧАСТИЧНО | ComparisonEngine/View, 2K/многослойность и headless UI smoke `2ad50af`; остаются визуальный smoke и финальная source-backed проверка wording. |
| 5 | ЧАСТИЧНО | Инженерный Excel и regression missing-price `a1e1a0a`; остаются визуальный/печать/PDF-конверсионный smoke. |
| 6 | ЧАСТИЧНО | PDF строится из `SystemCalculationResult`; multilayer/comparison/2K/unknown-price покрыты; cross-export regression `e3ef08d`; остаются визуальный/печать smoke. CI для `e3ef08d` ранее был queued и не является доказательством успеха до завершения run. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants + независимые golden cases 2/3/4/5 layers; успешный CI. |
| 8 | ВЫПОЛНЕНО | 2K учитывается как один смешанный материалный слой; TDS technology rules вынесены в §14. |
| 9 | НЕ ВЫПОЛНЕНО | Packaging/procurement workflow. |
| 10 | ЧАСТИЧНО | Alembic присутствует; acceptance migration/backup/rollback остаётся. |
| 11 | ЧАСТИЧНО | History/snapshot infrastructure есть; immutable snapshot contract остаётся. |
| 11.1 | НЕ ВЫПОЛНЕНО | Outbox/SMTP/retry/idempotency/safe secrets. |
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

## Закрытые этапы текущей ветки

### §3 — Ad hoc materials
Code commit: `42bb7fb282774e6f2c1691557ceba86d77795d21` (`test: cover ad hoc material normalization and persistence`).

### §4 — Comparison UI regression
Code commit: `2ad50af7c4de6b0b5ddbb0ef5113dbb023de2d8f`.
Headless Qt smoke создаёт `ComparisonView`, проверяет сравнение 2- и 4-слойных систем и наличие multilayer/technology/export controls. §4 не закрыт полностью из-за отсутствия визуального/source-backed acceptance.

### §5 — Missing-price regression
Code commit: `a1e1a0a1d7fd34c6fee3537dec39e98f13f6281c` (`test: preserve unknown prices in engineering Excel export`).
Unknown/no price сохраняется как неизвестный и в Excel выводится `—`, без выдуманной стоимости.

### §6 — Cross-export regression
Code commit: `e3ef08d3f6eae299ffe482a0dd8e557736334b2b` (`test: verify Excel and PDF engineering totals use same result`).
Regression строит один `SystemCalculationResult`, экспортирует его в Excel и PDF и сверяет количество слоёв, общий DFT и практический расход. Это подтверждает единый источник расчётных данных, но не заменяет визуальный/печатаемый smoke.

## §22 — Критическое ограничение
Не закрывать §22 до фактического подключения `LayerCompatibilityEngine` к пользовательскому workflow расчёта/системы. Наличие standalone engine/tests недостаточно.

Минимум для закрытия:
1. интеграция проверки в `CalculationView`;
2. интеграция проверки в `SystemsView`/редактор системы;
3. UI regression на положительный, отрицательный и `UNKNOWN` сценарии;
4. условия `previous_is_cured`, `recoat_elapsed_h`, `surface_prepared` только если они подтверждены TDS/источником;
5. `UNKNOWN` должен оставаться неизвестным и требовать проверки источника, а не автоматически становиться запретом.

## Порядок продолжения

1. Дождаться результата CI для `e3ef08d` и исправить регрессии, если CI красный.
2. Не закрывать §6 до визуального/печатаемого acceptance.
3. Далее идти по матрице к первому незакрытому этапу: §9, затем §10, §11, §11.1 и далее.
4. §22 вести отдельно, не закрывая его формально до полного workflow integration.
5. После каждого code commit сразу делать отдельный plan/docs commit с фактическим SHA и текущим статусом.

## История CI / контрольные точки
- `34439245472`
- `34439280625`
- `34440681323`
- `34437813196`
- Для `e3ef08d3f6eae299ffe482a0dd8e557736334b2b`: run `34451490167` был зафиксирован как `queued`; успех не считать подтверждённым, пока run не завершён.

## Следующий рабочий фокус
После подтверждения CI для §6 — начать §9 (packaging/procurement) отдельным code commit и отдельным plan commit. Параллельно сохранять §22 в статусе `ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ` до интеграции в основной workflow.
