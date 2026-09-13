# План развития LKMCalculator — АКЗ / ОГЗ / инженерный режим

> Живой план для ветки `v3.0-engineering-upgrade`.

## Правила
1. Не ломать существующий расчёт.
2. Инженерная логика — domain/service, не UI.
3. Excel не второй расчётный движок.
4. PDF и Excel из одного результата расчёта.
5. Инженерные и коммерческие данные не смешивать.
6. Существенный этап требует regression до закрытия.
7. Code commit, затем docs/plan commit.
8. `ВЫПОЛНЕНО` только с доказательством.
9. Отсутствующие данные = `UNKNOWN`.
10. GitHub Actions не запускать.
11. SPKEFFA — read-only TDS.

## Матрица статуса

| § | Статус | Состояние / следующий шаг |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро. |
| 2 | ЧАСТИЧНО | UI smoke нужен PySide6. |
| 3 | ВЫПОЛНЕНО | AdHocMaterialDialog. |
| 4 | ЧАСТИЧНО | Comparison/2K; smoke remains. |
| 5 | ЧАСТИЧНО | Engineering Excel; visual remains. |
| 6 | ЧАСТИЧНО | PDF; visual remains. |
| 7 | ВЫПОЛНЕНО | Precision invariants. |
| 8 | ВЫПОЛНЕНО | 2K один слой. |
| 9 | ВЫПОЛНЕНО | PackagingPlanner. |
| 10 | ВЫПОЛНЕНО | Alembic + backup/restore. |
| 11 | ВЫПОЛНЕНО | Snapshot integrity. |
| 11.1 | ВЫПОЛНЕНО | Durable outbox. |
| 12 | ЧАСТИЧНО | Engineering context + TDS traces. |
| 13 | ЧАСТИЧНО | Surface condition + UI. |
| 14 | ЧАСТИЧНО | SPKEFFA KNOWN rules. |
| 15 | ОТЛОЖЕНО | OGZ. |
| 16 | ЧАСТИЧНО | Recommendations. |
| 17 | ЧАСТИЧНО | Inspection DFT UI. |
| 18 | ЧАСТИЧНО | Evidence log заполнен (core **94 passed**, 2026-09-13). Full suite + UI PENDING. `docs/release_acceptance_v3.md`. |
| 19 | ВЫПОЛНЕНО | Legacy parity VERIFIED. |
| 20 | ЧАСТИЧНО | KB + Системы 1–4. |
| 21 | ЧАСТИЧНО | Compatibility matrix. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | LKM-Prof Table 1. |
| 23 | ЧАСТИЧНО | Pre-Application. |
| 24 | ЧАСТИЧНО | Chemical resistance. |
| 25 | ЧАСТИЧНО | Catalog KNOWN rules. |
| 26 | ЧАСТИЧНО | Explanation. |
| 27 | ЧАСТИЧНО | Staging. |
| 28 | ВЫПОЛНЕНО | LossProfile. |
| 29 | ЧАСТИЧНО | confirm_draft. |
| 30 | ВЫПОЛНЕНО | Decision Log. |
| 31 | ЧАСТИЧНО | Scenario. |
| 32 | ЧАСТИЧНО | DFT inspection. |

## Stages

- §18 evidence: `docs/release_acceptance_v3.md` — core subset 94 passed (2026-09-13).
- SPKEFFA read-only.
