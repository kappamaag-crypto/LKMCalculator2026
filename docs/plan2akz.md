# План развития LKMCalculator — АКЗ / ОГЗ / инженерный режим

> Живой план для ветки `v3.0-engineering-upgrade`.

## Правила
1. Не ломать расчёт.
2. Инженерная логика — domain/service.
3. Excel не второй движок.
4. PDF/Excel из одного результата.
5. Не смешивать инженерные/коммерческие данные.
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
| 23 | ВЫПОЛНЕНО | Pre-Application domain/service. |
| 24 | ВЫПОЛНЕНО | Source-backed only; empty⇒UNKNOWN; promote gate; conc/temp limits. Evidence: `test_chemical_resistance.py` (12). Agent catalog expansion remains §25. |
| 25 | ЧАСТИЧНО | Catalog KNOWN. |
| 26 | ЧАСТИЧНО | Explanation Engine domain/service wired; regression tests added (`test_explanation_engine.py`), existing dialog smoke plus main-window acceptance smoke (`test_explanation_dialog_smoke.py`, `test_explanation_main_window_smoke.py`). Local pytest execution remains pending; UI/E2E acceptance is implemented but not execution-proven. |
| 27 | ЧАСТИЧНО | Staging. |
| 28 | ВЫПОЛНЕНО | LossProfile. |
| 29 | ЧАСТИЧНО | confirm_draft. |
| 30 | ВЫПОЛНЕНО | Decision Log. |
| 31 | ЧАСТИЧНО | Scenario. |
| 32 | ЧАСТИЧНО | DFT inspection. |

## Stages

- §23/§24 domain closed.
- §26: domain/service + regression + dialog smoke + main-window acceptance test are implemented; not closed because local pytest execution remains pending and the acceptance tests have not been execution-proven.
- §32: DFT domain/service workflow and headless UI smoke exist. Added regression coverage for missing acceptance bands ⇒ `UNKNOWN`, missing measured value ⇒ `UNKNOWN`, out-of-range evaluation, and the invariant that DFT binding does not auto-set inspection acceptance. Tests are not execution-proven while the local repository/test environment remains unavailable.
- SPKEFFA read-only.
