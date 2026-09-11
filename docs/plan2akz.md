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
| 2 | ЧАСТИЧНО | Динамический редактор есть; добавлен headless smoke-тест основного workflow (расчёт + загрузка сохранённой системы); остаются фактический pytest-run и полный UI smoke. |
| 3 | ВЫПОЛНЕНО | AdHocMaterialDialog, normalisation, duplicate reuse, persistence. |
| 4 | ЧАСТИЧНО | Comparison/2K/multilayer есть; остаются smoke и source-backed wording. |
| 5 | ЧАСТИЧНО | Engineering Excel есть; остаётся визуальная/печатаемая проверка. |
| 6 | ЧАСТИЧНО | PDF из SystemCalculationResult; остаётся visual/print smoke. |
| 7 | ВЫПОЛНЕНО | Precision/unit invariants и golden multilayer cases. |
| 8 | ВЫПОЛНЕНО | 2K — один смешанный материалный слой; TDS rules вынесены в §14. |
| 9 | ЧАСТИЧНО | PackagingPlanner; склада нет и не добавлять. |
| 10 | ЧАСТИЧНО | Alembic + SQLite backup/restore; acceptance позже. |
| 11 | ЧАСТИЧНО | Material snapshots/verified reads/integrity hashing; runtime acceptance позже. |
| 11.1 | ЧАСТИЧНО | Durable notification outbox; runtime/SMTP acceptance позже. |
| 12 | ЧАСТИЧНО | Engineering context + History TDS traces (v8) + HistoryView TDS UI. Broader runtime acceptance remains. |
| 13 | ЧАСТИЧНО | Surface preparation/profile/condition + UI; acceptance позже. |
| 14 | ЧАСТИЧНО | All 10 SPKEFFA catalog docs have KNOWN rules + full service/UI wiring (template, calc, recommend default, History). Broader E2E acceptance remains. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Legacy ranking + compatibility warnings; полная scoring остаётся. |
| 17 | ЧАСТИЧНО | Inspection domain/service/UI; добавлен DFT UI workflow; acceptance позже. |
| 18 | ЧАСТИЧНО | Release acceptance checklist; evidence PENDING. |
| 19 | ЧАСТИЧНО | Legacy parity matrix; строки PENDING. |
| 20 | ЧАСТИЧНО | KB + Системы 1–4 + staging + Review + editor + controlled incomplete Material. Остаются полное сопоставление и UI acceptance. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix; каталог не заменяет TDS/НД. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | CompatibilityEngine интегрирован; реальные TDS-backed conditions и UI acceptance остаются. |
| 23 | ЧАСТИЧНО | Domain PreApplicationCheck (READY/BLOCKED/INCOMPLETE) + CalculationService.run_pre_application_check; surface/ambient/material limits; no invented dew-margin. Добавлен read-only UI диалог из последнего расчёта с повторной проверкой и headless smoke. Остаются фактический pytest-run и полный E2E с подтверждёнными шаблонами/источниками НД и inspection workflow (§32). |
| 24 | ЧАСТИЧНО | Domain ChemicalResistanceRule/check + promote gate + CalculationService; empty registry ⇒ UNKNOWN (no invention). Catalog of promoted TDS-backed agents and UI remain. |
| 25 | ЧАСТИЧНО | Full catalog KNOWN rules + normative/History/recommend/template chain. Broader E2E acceptance remains. |
| 26 | ЧАСТИЧНО | Explanation + LayerResult losses provenance (EXPLICIT/PROFILE/DEFAULT) + bundle; 17 unit tests; ExplanationDialog + headless dialog smoke-test; MainWindow exposes «Пояснение расчёта…». Остаются фактический pytest-run и E2E acceptance. |
| 27 | ЧАСТИЧНО | Staging, matching, provenance, System Template и controlled incomplete Material реализованы; TDS enrichment/acceptance остаются. |
| 28 | ВЫПОЛНЕНО | Controlled LossProfile. |
| 29 | ЧАСТИЧНО | Catalogue → draft → editor TDS gate → CONFIRM. Coverage = all catalogued SPKEFFA docs with KNOWN rules. |
| 30 | ВЫПОЛНЕНО | Engineering Decision Log. |
| 31 | ЧАСТИЧНО | Scenario service/UI + confirmed-template bridge; acceptance remains. |
| 32 | ЧАСТИЧНО | Domain DFT evaluate + bind into InspectionRecord + service + 15 tests; добавлен UI для ввода DFT-точек, проверки против последнего расчёта и формирования записи с DFT. Остаются фактический pytest-run, полный E2E, multi-layer acceptance policy. |

## Каталог `Системы 1–4`

Файлы в `books/`: `Системы 1.xls`, `Системы 2.XLSX`, `Системы 3.xlsx`, `Системы 4.xlsx`.

Каталог является исходным набором вариантов систем и кандидатов материалов, но не TDS/нормативом. Сохраняются file/sheet/row/SHA-256; неизвестное/неоднозначное = `UNKNOWN`; автоматического доказательства применимости нет.

## Реализованные code stages

- `tds_manifest.py` — TDS document/rule verification boundary.
- `spk_effa_tds_catalog.py` — measured binary SHA-256 catalog for 10 SPKEFFA TDS PDFs.
- `tds_rule_promotion.py` — explicit promote_tds_rule gate; parse_dft_range_um.
- `tds_known_rules.py` — Tank LP + EFFA 01B + prior Blank rules; longest-hint resolve.
- `tds_technology_bridge.py` — DFT checks + enrich_filter_result_with_known_tds.
- `tds_normative_bridge.py` — KNOWN TDS → NormativeModel / EngineeringContext.
- `pre_application.py` — Pre-Application Check READY/BLOCKED/INCOMPLETE.
- `chemical_resistance.py` — source-backed chemical resistance only.
- `chemical_resistance_rules.py` — promote gate; empty registry by default.
- `explanation.py` — Explanation Engine (source-traceable report for SystemCalculationResult).
- `explanation_dialog.py` — read-only Qt dialog for ExplanationReport; no engineering logic in UI.
- `pre_application_dialog.py` — read-only Qt surface for Pre-Application status/checklist; reruns the existing service against the latest calculation result.
- `main_window.py` — «Инженерное → Pre-Application Check…» opens the checklist for the last completed calculation; no calculation => returns user to «Расчёт».
- `main_window.py` — «Инженерное → Пояснение расчёта…» открывает ExplanationDialog для последнего завершённого расчёта; без расчёта переводит пользователя на экран «Расчёт».
- `inspection_view.py` — DFT point input, evaluation against latest SystemCalculationResult, and DFT-bound inspection record creation.
- DFT inspection evaluate + limits_from_calculation_result (§32 partial).
- LayerResult losses provenance + ResolvedLosses (§26/§28).
- `test_calculation_view_smoke.py` — headless CalculationView workflow coverage for direct calculation and saved-system restore; test execution remains pending because this connector-only session has no runnable repository checkout.
- `test_explanation_dialog_smoke.py` — headless ExplanationDialog rendering coverage; test execution remains pending for the same reason.
- `test_pre_application_dialog_smoke.py` — headless Pre-Application dialog rendering/UNKNOWN preservation coverage; test execution remains pending for the same reason.
- `test_inspection_view_smoke.py` — headless DFT InspectionView evaluation against a calculation result; test execution remains pending for the same reason.

## TDS verification boundary — §12/§14/§25

`kappamaag-crypto/SPKEFFA` — read-only. Git blob SHA-1 ≠ binary PDF SHA-256.

Document KNOWN requires path + binary SHA-256. Rule KNOWN requires explicit promote_tds_rule(document, rule, verified_by=...). Extracted text alone does not promote.

## §14/§25 — progress

Done:
- binary SHA-256 document catalog (10 SPKEFFA TDS PDFs);
- promote gate;
- KNOWN rules for all catalog documents including **Blank Tank LP** and **EFFA 01B**;
- longest-hint material→document resolution;
- TDS DFT technology bridge;
- template `tds_verified` evaluation + editor status;
- RecommendationService.recommend(apply_known_tds_dft=True by default);
- tds_normative_bridge → EngineeringContext;
- HistoryService snapshot v8 TDS traces + HistoryView TDS column/detail;
- CalculationService TDS helpers;
- domain remains free of service imports;
- **pushed to origin via GitHub connector** (2026-09-11).

Still open:
- broader end-to-end UI/runtime acceptance beyond unit/smoke coverage.

## §23 — Pre-Application Check

Done:
- `domain/pre_application.py` — pure checklist: ambient, surface, per-material technology limits;
- status READY / BLOCKED / INCOMPLETE; missing data = UNKNOWN (no default 3 °C dew-point margin);
- `CalculationService.run_pre_application_check` service entry;
- unit tests `test_pre_application.py` (8 cases);
- `ui/dialogs/pre_application_dialog.py` — read-only checklist dialog bound to the latest `SystemCalculationResult`, with explicit re-check;
- `MainWindow` menu entry `Инженерное → Pre-Application Check…`;
- `tests/test_pre_application_dialog_smoke.py` — headless rendering/UNKNOWN smoke.

Still open:
- фактический pytest-run (отложен согласно текущему правилу плана);
- full E2E with confirmed templates, verified TDS sources and inspection workflow;
- broader acceptance evidence before marking §23 `ВЫПОЛНЕНО`.

## §24 — Chemical resistance (source-backed only)

Done:
- `domain/chemical_resistance.py` — ChemicalAgent, ChemicalResistanceRule, check_chemical_resistance;
- outcome RESISTANT / NOT_RESISTANT only when status=KNOWN + NormativeSource; else UNKNOWN;
- no inference from binder type / corrosion category;
- `services/chemical_resistance_rules.py` — promote gate + empty registry by default;
- `CalculationService.check_chemical_resistance`;
- tests `test_chemical_resistance.py` (9 cases).

Still open:
- populate KNOWN rules only after verified TDS/НД excerpts;
- recommendation filter / UI exposure;
- concentration–temperature matrix per product family.

## §26 — Explanation Engine

Done:
- `domain/explanation.py` — ExplanationItem / ExplanationReport; explain_system_calculation;
- explains DFT/WFT basis (SV only), losses resolved value + zero/default note (§28), engineering context normative/surface status, cost UNKNOWN vs known, incomplete material;
- no invented values; intermediate no-round note;
- `explain_engineering_bundle` + `explain_pre_application` / `explain_chemical_resistance` / `explain_recommendation_signals` (optional fold; empty chem → UNKNOWN);
- `CalculationService.explain_calculation` / `explain_engineering_bundle` / `format_explanation`;
- LayerResult.losses_source / losses_profile_name / losses_note; ResolvedLosses in calculator;
- tests `test_explanation.py` (17 cases, including EXPLICIT/PROFILE/DEFAULT provenance);
- `ui/dialogs/explanation_dialog.py` — read-only source-traceable report dialog;
- `tests/test_explanation_dialog_smoke.py` — headless rendering assertions;
- `ui/main_window.py` — menu `Инженерное → Пояснение расчёта…` invokes `CalculationService.explain_calculation` for the last completed calculation and presents `ExplanationDialog`; when no result exists, the user is sent to the calculation tab.

Still open:
- фактический pytest-run (отложен согласно текущему правилу плана);
- полный E2E acceptance.

## §32 — Inspection / DFT workflow

Done:
- `domain/inspection.py` — DftLayerLimits, DftMeasurementPoint, DftPointEvaluation, DftInspectionReport;
- `evaluate_dft_inspection` pure compare; target alone ≠ acceptance band; missing min/max → UNKNOWN_LIMITS (no invented tolerance);
- `limits_from_calculation_result` from SystemCalculationResult + optional material.recommended_dft_*;
- InspectionRecord binds `dft_points` / `dft_overall_status` / `dft_summary` via `with_dft_report` (acceptance_status never auto-set from DFT);
- `InspectionService.evaluate_dft` / `evaluate_dft_against_calculation` / `bind_dft_report` / `create_record_with_dft*`;
- tests `test_inspection_workflow.py` (15 cases);
- `ui/views/inspection_view.py` — DFT layer/point/measurement/instrument input; evaluation against the latest completed calculation; creation of an InspectionRecord with the DFT report bound without changing acceptance status;
- `tests/test_inspection_view_smoke.py` — headless UI workflow smoke.

Still open:
- фактический pytest-run (отложен согласно текущему правилу плана);
- полный E2E с подтверждённым шаблоном/источником НД;
- multi-layer acceptance aggregation policy beyond current overall status.

## §28 / §30 — закрыты ранее

Controlled LossProfile and Engineering Decision Log remain closed.
