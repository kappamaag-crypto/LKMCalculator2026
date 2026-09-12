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
10. GitHub Actions не запускать. Тесты пока не запускать; общий прогон позже по отдельной команде.
11. `kappamaag-crypto/SPKEFFA` — только read-only источник TDS; его не изменять.

## Матрица статуса

| § | Статус | Состояние / следующий шаг |
|---|---|---|
| 1 | ВЫПОЛНЕНО | Базовое ядро расчёта сохранено. |
| 2 | ЧАСТИЧНО | Динамический редактор есть; добавлен headless smoke-тест основного workflow; остаются полный UI smoke. |
| 3 | ВЫПОЛНЕНО | AdHocMaterialDialog, normalisation, duplicate reuse, persistence. |
| 4 | ЧАСТИЧНО | Comparison/2K/multilayer есть; остаются smoke и source-backed wording. |
| 5 | ЧАСТИЧНО | Engineering Excel есть; остаётся визуальная/печатаемая проверка. |
| 6 | ЧАСТИЧНО | PDF из SystemCalculationResult; остаётся visual/print smoke. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants и golden multilayer cases. |
| 8 | ВЫПОЛНЕНО | 2K — один смешанный материальный слой; TDS rules вынесены в §14. |
| 9 | ЧАСТИЧНО | PackagingPlanner; склада нет и не добавлять. |
| 10 | ЧАСТИЧНО | Alembic + SQLite backup/restore; acceptance позже. |
| 11 | ЧАСТИЧНО | Material snapshots/verified reads/integrity hashing; runtime acceptance позже. |
| 11.1 | ЧАСТИЧНО | Durable notification outbox; runtime/SMTP acceptance позже. |
| 12 | ЧАСТИЧНО | Engineering context + History TDS traces (v8) + HistoryView TDS UI. Broader runtime acceptance remains. |
| 13 | ЧАСТИЧНО | Surface preparation/profile/condition + UI; acceptance позже. |
| 14 | ЧАСТИЧНО | All 10 SPKEFFA catalog docs have KNOWN rules + full service/UI wiring. Broader E2E acceptance remains. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Legacy ranking + compatibility warnings; ScoreBreakdown в RecommendationItem/View. |
| 17 | ЧАСТИЧНО | Inspection domain/service/UI; DFT UI workflow; acceptance позже. |
| 18 | ЧАСТИЧНО | Release acceptance checklist; evidence PENDING. |
| 19 | ВЫПОЛНЕНО | Legacy parity matrix: formulas / multilayer / unknown / 2K / comparison / recommendations / excel / pdf / history / persistence / UI / systems editor VERIFIED. Qt visual E2E remains in §20. |
| 20 | ЧАСТИЧНО | KB + Системы 1–4 + staging + Review + editor + incomplete Material. Остаются полный UI/E2E acceptance. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix; каталог не заменяет TDS/НД. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | LayerCompatibilityEngine + LKM-Prof Table 1; empty=UNKNOWN. TDS-backed material conditions remain. |
| 23 | ЧАСТИЧНО | Pre-Application READY/BLOCKED/INCOMPLETE; no invented dew-margin. E2E remains. |
| 24 | ЧАСТИЧНО | Chemical resistance source-backed only; empty registry ⇒ UNKNOWN. |
| 25 | ЧАСТИЧНО | Full catalog KNOWN rules + normative/History/recommend/template chain. |
| 26 | ЧАСТИЧНО | Explanation + losses provenance; E2E remains. |
| 27 | ЧАСТИЧНО | Staging/matching/provenance; TDS enrichment remains. |
| 28 | ВЫПОЛНЕНО | Controlled LossProfile. |
| 29 | ЧАСТИЧНО | confirm_draft service gate; UI/E2E remains. |
| 30 | ВЫПОЛНЕНО | Engineering Decision Log. |
| 31 | ЧАСТИЧНО | Scenario service/UI; acceptance remains. |
| 32 | ЧАСТИЧНО | DFT inspection evaluate + UI; multi-layer policy / E2E remain. |

## Реализованные code stages

- §19 formula / multilayer / unknown / 2K / comparison / recommendations / export / history / persistence VERIFIED.
- §19 UI + systems editor source-contract parity: `test_legacy_ui_workflow_parity.py` (7 cases); matrix rows → VERIFIED. Qt E2E remains §20.

## TDS verification boundary — §12/§14/§25

`kappamaag-crypto/SPKEFFA` — read-only. Document KNOWN requires path + binary PDF SHA-256.

## §28 / §30 — закрыты ранее

Controlled LossProfile and Engineering Decision Log remain closed.
