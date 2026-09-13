# План развития LKMCalculator — АКЗ / ОГЗ / инженерный режим

> Живой план для ветки `v3.0-engineering-upgrade`.

## Правила
1. Не ломать расчёт.
2. Инженерная логика — domain/service.
3. Excel не второй движок.
4. PDF/Excel из одного результата.
5. Не смешивать инженерные и коммерческие данные.
6. Regression до закрытия.
7. Code commit, затем docs.
8. `ВЫПОЛНЕНО` с доказательством.
9. Отсутствующие = `UNKNOWN`.
10. GitHub Actions не запускать.
11. SPKEFFA read-only.

## Матрица статуса

| § | Статус | Состояние |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро. |
| 2 | ЧАСТИЧНО | UI smoke — PySide6. |
| 3 | ВЫПОЛНЕНО | AdHocMaterialDialog. |
| 4 | ЧАСТИЧНО | Comparison/2K. |
| 5 | ЧАСТИЧНО | Engineering Excel. |
| 6 | ЧАСТИЧНО | PDF. |
| 7 | ВЫПОЛНЕНО | Precision. |
| 8 | ВЫПОЛНЕНО | 2K. |
| 9 | ВЫПОЛНЕНО | PackagingPlanner. |
| 10 | ВЫПОЛНЕНО | Alembic + backup. |
| 11 | ВЫПОЛНЕНО | Snapshot integrity. |
| 11.1 | ВЫПОЛНЕНО | Outbox. |
| 12 | ЧАСТИЧНО | Engineering context. |
| 13 | ЧАСТИЧНО | Surface condition. |
| 14 | ЧАСТИЧНО | SPKEFFA rules. |
| 15 | ОТЛОЖЕНО | OGZ. |
| 16 | ЧАСТИЧНО | Recommendations. |
| 17 | ЧАСТИЧНО | Inspection DFT UI. |
| 18 | ЧАСТИЧНО | Evidence log; full suite PENDING. |
| 19 | ВЫПОЛНЕНО | Legacy parity. |
| 20 | ЧАСТИЧНО | KB / Системы. |
| 21 | ЧАСТИЧНО | Compatibility. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | LKM-Prof Table 1. |
| 23 | ВЫПОЛНЕНО | READY/BLOCKED/INCOMPLETE; no invented dew; RH/contamination/service. `test_pre_application.py` (11). UI E2E §2. |
| 24 | ЧАСТИЧНО | Chemical resistance. |
| 25 | ЧАСТИЧНО | Catalog KNOWN. |
| 26 | ЧАСТИЧНО | Explanation. |
| 27 | ЧАСТИЧНО | Staging. |
| 28 | ВЫПОЛНЕНО | LossProfile. |
| 29 | ЧАСТИЧНО | confirm_draft. |
| 30 | ВЫПОЛНЕНО | Decision Log. |
| 31 | ЧАСТИЧНО | Scenario. |
| 32 | ЧАСТИЧНО | DFT inspection. |

## Stages

- §23 closed: `test_pre_application.py` (11).
- SPKEFFA read-only.
