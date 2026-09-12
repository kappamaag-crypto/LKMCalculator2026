# План развития LKMCalculator — АКЗ / ОГЗ / инженерный режим

> Живой план для ветки `v3.0-engineering-upgrade`. Статус меняется только по фактическому состоянию кода и проверок.

## Правила
1. Не ломать существующий расчёт.
2. Инженерная логика — domain/service, не UI.
3. Excel не является вторым расчётным движком.
4. PDF и Excel получают данные из одного результата расчёта.
5. Инженерные и коммерческие/закупочные данные не смешивать без явного назначения.
6. Существенный этап требует regression/smoke-проверки до закрытия.
7. Существенный этап — отдельный code commit; после него — отдельный docs/plan commit.
8. `ВЫПОЛНЕНО` только при реализации и проверочном доказательстве.
9. Отсутствующие/непроверенные данные = `UNKNOWN`.
10. GitHub Actions не запускать.
11. `kappamaag-crypto/SPKEFFA` — только read-only источник TDS.

## Матрица статуса

| § | Статус | Состояние / следующий шаг |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро расчёта сохранено. |
| 2 | ЧАСТИЧНО | UI smoke нужен PySide6. |
| 3 | ВЫПОЛНЕНО | AdHocMaterialDialog + persistence. |
| 4 | ЧАСТИЧНО | Comparison/2K/multilayer; added UNKNOWN-cost regression; smoke remains. |
| 5 | ЧАСТИЧНО | Engineering Excel; added customer Excel print-layout regression; actual pytest/visual print remains. |
| 6 | ЧАСТИЧНО | PDF; visual/print remains. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants. |
| 8 | ВЫПОЛНЕНО | 2K — один смешанный слой. |
| 9 | ВЫПОЛНЕНО | PackagingPlanner; склад не добавлен. |
| 10 | ВЫПОЛНЕНО | Alembic + SQLite backup/restore. |
| 11 | ВЫПОЛНЕНО | SHA-256 seal/verify + material restore. |
| 11.1 | ВЫПОЛНЕНО | Durable outbox: idempotency, retry/FAILED, worker gate, без SMTP secrets в БД. Evidence: `test_notification_outbox.py` (6). Live SMTP optional. |
| 12 | ЧАСТИЧНО | Engineering context + History TDS traces (v8). |
| 13 | ЧАСТИЧНО | Surface preparation/profile/condition + UI. |
| 14 | ЧАСТИЧНО | SPKEFFA KNOWN rules; E2E remains. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Recommendations + ScoreBreakdown. |
| 17 | ЧАСТИЧНО | Inspection DFT UI. |
| 18 | ЧАСТИЧНО | Release acceptance checklist; evidence PENDING. |
| 19 | ВЫПОЛНЕНО | Legacy parity matrix VERIFIED. |
| 20 | ЧАСТИЧНО | KB + Системы 1–4; UI/E2E remains. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | LKM-Prof Table 1; empty=UNKNOWN. |
| 23 | ЧАСТИЧНО | Pre-Application; no invented dew-margin. |
| 24 | ЧАСТИЧНО | Chemical resistance source-backed only. |
| 25 | ЧАСТИЧНО | Full catalog KNOWN rules chain. |
| 26 | ЧАСТИЧНО | Explanation + losses provenance. |
| 27 | ЧАСТИЧНО | Staging/matching/provenance. |
| 28 | ВЫПОЛНЕНО | Controlled LossProfile. |
| 29 | ЧАСТИЧНО | confirm_draft service gate. |
| 30 | ВЫПОЛНЕНО | Engineering Decision Log. |
| 31 | ЧАСТИЧНО | Scenario service/UI. |
| 32 | ЧАСТИЧНО | DFT inspection; strict multi-layer coverage policy implemented; runtime/E2E acceptance remains. |

## Реализованные code stages

- §9/§10/§11/§19 closed.
- §11.1 outbox closed: `test_notification_outbox.py` (6 cases).
- §32 DFT multi-layer policy: calculation-backed inspection requires at least one measured point for every calculated layer by default; missing layer coverage remains `UNKNOWN` and is explicitly reported.
- §5 customer Excel print-layout regression added: 2-layer and 5-layer cases assert dynamic print area, repeated header rows, fit-to-page, and totals row.
- §4 comparison cost provenance regression added: missing thinner cost remains `UNKNOWN` instead of being coerced to zero; explicit zero remains zero.

## TDS verification boundary — §12/§14/§25

`kappamaag-crypto/SPKEFFA` — read-only.

## §28 / §30 — закрыты ранее

Controlled LossProfile and Engineering Decision Log remain closed.
