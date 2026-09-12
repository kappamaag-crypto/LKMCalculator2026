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
| 2 | ЧАСТИЧНО | Динамический редактор; headless smoke; полный UI smoke нужен PySide6. |
| 3 | ВЫПОЛНЕНО | AdHocMaterialDialog, normalisation, duplicate reuse, persistence. |
| 4 | ЧАСТИЧНО | Comparison/2K/multilayer; smoke/source-backed wording remains. |
| 5 | ЧАСТИЧНО | Engineering Excel; visual/print remains. |
| 6 | ЧАСТИЧНО | PDF из SystemCalculationResult; visual/print remains. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants и golden multilayer cases. |
| 8 | ВЫПОЛНЕНО | 2K — один смешанный слой; TDS в §14. |
| 9 | ВЫПОЛНЕНО | PackagingPlanner; склад не добавлен. `test_packaging.py` (8). |
| 10 | ВЫПОЛНЕНО | Alembic head `007_system_templates` + SQLite online backup/restore. Evidence: `test_database_safety.py` (7 cases). |
| 11 | ЧАСТИЧНО | Material snapshots/verified reads/integrity hashing; runtime acceptance позже. |
| 11.1 | ЧАСТИЧНО | Durable notification outbox; runtime/SMTP acceptance позже. |
| 12 | ЧАСТИЧНО | Engineering context + History TDS traces (v8) + HistoryView TDS UI. |
| 13 | ЧАСТИЧНО | Surface preparation/profile/condition + UI. |
| 14 | ЧАСТИЧНО | SPKEFFA catalog KNOWN rules + wiring; E2E remains. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Recommendations + ScoreBreakdown. |
| 17 | ЧАСТИЧНО | Inspection DFT UI; acceptance позже. |
| 18 | ЧАСТИЧНО | Release acceptance checklist; evidence PENDING. |
| 19 | ВЫПОЛНЕНО | Legacy parity matrix все строки VERIFIED. |
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
| 32 | ЧАСТИЧНО | DFT inspection; multi-layer policy remains. |

## Реализованные code stages

- §19 parity closed; §9 PackagingPlanner closed.
- §10 Alembic + SQLite backup/restore closed: `test_database_safety.py` (7 cases).

## TDS verification boundary — §12/§14/§25

`kappamaag-crypto/SPKEFFA` — read-only.

## §28 / §30 — закрыты ранее

Controlled LossProfile and Engineering Decision Log remain closed.
