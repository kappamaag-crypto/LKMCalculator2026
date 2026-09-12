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
| 16 | ЧАСТИЧНО | Legacy ranking + compatibility warnings; ScoreBreakdown сохранён в RecommendationItem и теперь прозрачно отображается в RecommendationView и текстовом отчёте. Остаются фактический pytest-run и полная scoring/E2E-проверка. |
| 17 | ЧАСТИЧНО | Inspection domain/service/UI; добавлен DFT UI workflow; acceptance позже. |
| 18 | ЧАСТИЧНО | Release acceptance checklist; evidence PENDING. |
| 19 | ЧАСТИЧНО | Legacy parity matrix; **formulas / multilayer / unknown / 2K / comparison / recommendations / excel / pdf / history / persistence** VERIFIED. PENDING: UI, systems editor. |
| 20 | ЧАСТИЧНО | KB + Системы 1–4 + staging + Review + editor + incomplete Material. Side-by-side DRAFT + expand + load_reviewed + CatalogReview + bind/prepare + `confirm_draft` (service gate: unique material + provenance + tds_verified=KNOWN → CONFIRMED; prepare never auto-CONFIRM). Системы 1/4 layout N/A. Остаются фактический pytest-run и полный UI/E2E acceptance. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix; каталог не заменяет TDS/НД. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | `LayerCompatibilityEngine` использует точную матрицу из `books/совместимость_лкм.png` (Таблица 1) с опубликованным источником LKM-Prof; пустая ячейка = UNKNOWN, 1 = WARNING/проверка адгезии, 2 = WARNING/требуется шероховатость. Матрица участвует в `CalculationService` summary/UI, source identity зафиксирована в коде и regression-test. Остаются реальные material-specific TDS-backed conditions и полноценный UI/E2E acceptance. |
| 23 | ЧАСТИЧНО | Domain PreApplicationCheck (READY/BLOCKED/INCOMPLETE) + CalculationService.run_pre_application_check; surface/ambient/material limits; no invented dew-margin. Добавлен read-only UI диалог из последнего расчёта с повторной проверкой и headless smoke. Остаются фактический pytest-run и полный E2E с подтверждёнными шаблонами/источниками НД и inspection workflow (§32). |
| 24 | ЧАСТИЧНО | Domain ChemicalResistanceRule/check + promote gate + CalculationService; empty registry ⇒ UNKNOWN (no invention). Добавлен opt-in hard-filter химстойкости в RecommendationService и тесты; UI диалог/меню уже есть; RecommendationView теперь передаёт явную химсреду в hard-filter. Остаются каталог KNOWN TDS-backed agents и concentration–temperature matrix. |
| 25 | ЧАСТИЧНО | Full catalog KNOWN rules + normative/History/recommend/template chain. Broader E2E acceptance remains. |
| 26 | ЧАСТИЧНО | Explanation + LayerResult losses provenance (EXPLICIT/PROFILE/DEFAULT) + bundle; 17 unit tests; ExplanationDialog + headless dialog smoke-test; MainWindow exposes «Пояснение расчёта…». Остаются фактический pytest-run и E2E acceptance. |
| 27 | ЧАСТИЧНО | Staging, matching, provenance, System Template и controlled incomplete Material реализованы; TDS enrichment/acceptance остаются. |
| 28 | ВЫПОЛНЕНО | Controlled LossProfile. |
| 29 | ЧАСТИЧНО | Catalogue → draft → unique bind → prepare → `can_confirm` → `confirm_draft` → persist. Service-level CONFIRM gate covered by regression. Остаются фактический pytest-run и полный UI/E2E acceptance. |
| 30 | ВЫПОЛНЕНО | Engineering Decision Log. |
| 31 | ЧАСТИЧНО | Scenario service/UI + confirmed-template bridge; acceptance remains. |
| 32 | ЧАСТИЧНО | Domain DFT evaluate + bind into InspectionRecord + service + 15 tests; добавлен UI для ввода DFT-точек, проверки против последнего расчёта и формирования записи с DFT. Остаются фактический pytest-run, полный E2E, multi-layer acceptance policy. |

## Каталог `Системы 1–4`

Файлы в `books/`: `Системы 1.xls`, `Системы 2.XLSX`, `Системы 3.xlsx`, `Системы 4.xlsx`.

Каталог является исходным набором вариантов систем и кандидатов материалов, но не TDS/нормативом. Сохраняются file/sheet/row/SHA-256; неизвестное/неоднозначное = `UNKNOWN`; автоматического доказательства применимости нет.

Staging boundary (v3):
- `SystemBookImporter` читает только сырые ячейки + identity (path/SHA-256); не угадывает колонки.
- `SystemBookMapper` принимает **явную** `SystemBookColumnMap` и строит только `DRAFT` `SystemTemplateDraft` с provenance; `tds_verified=UNKNOWN` до review/TDS gate.
- `SystemBookSideBySideMapper` + reviewed layouts: SYSTEMS2_AKZ/OGZ, SYSTEMS3_AKZ/OGZ; registry `REVIEWED_SIDE_BY_SIDE_LAYOUTS` (4 entries).
- `expand_reviewed_workbook(path)` — expand only sheets with explicit layout; others skipped (no guessing).
- `SystemTemplateService.load_reviewed_side_by_side_drafts` — service entry; status DRAFT, tds_verified UNKNOWN.
- `bind_unique_materials` / `prepare_reviewed_draft_for_review` — unique name→material_id only; then TDS evaluate; never auto-CONFIRM.
- `confirm_draft` — explicit service CONFIRM only when can_confirm; editor uses this gate.
- CatalogReview UI: table + open via prepare path; no DB write on load.
- Одна строка → один DRAFT; «-» skipped; unit-suffix OK; composite → DFT UNKNOWN.
- Системы 1.xls empty/corrupt; Системы 4.xlsx empty — layout N/A (documented).
- Остаются полный UI/E2E acceptance и явный TDS gate → CONFIRM при KNOWN.

## Реализованные code stages

- §19 formula / multilayer / unknown / 2K / comparison / recommendations / export / history / material persistence parity VERIFIED.
- §19 material persistence parity: `test_legacy_persistence_parity.py` (5 cases); matrix row Material persistence → VERIFIED.
- Remaining §19 PENDING: UI calculation workflow, systems editor.

## TDS verification boundary — §12/§14/§25

`kappamaag-crypto/SPKEFFA` — read-only. Git blob SHA-1 ≠ binary PDF SHA-256.

Document KNOWN requires path + binary PDF SHA-256. Rule KNOWN requires explicit promote_tds_rule(document, rule, verified_by=...). Extracted text alone does not promote.

## §28 / §30 — закрыты ранее

Controlled LossProfile and Engineering Decision Log remain closed.
