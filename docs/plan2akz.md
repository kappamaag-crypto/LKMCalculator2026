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
| 2 | ЧАСТИЧНО | Динамический редактор есть; остаются workflow/UI smoke. |
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
| 12 | ЧАСТИЧНО | Engineering context/source identity/History/verified loader; first KNOWN TDS rules exist, full integration remains. |
| 13 | ЧАСТИЧНО | Surface preparation/profile/condition + UI; acceptance позже. |
| 14 | ЧАСТИЧНО | Document SHA-256 catalog + explicit promote_tds_rule gate + first KNOWN rules (Blank Universal/Finish DFT, solids, density) + TDS DFT technology bridge. Still open: more materials, full tech stack wiring, UI/template tds_verified. |
| 15 | ОТЛОЖЕНО | OGZ ПТМ / section factor / R / critical temperature. |
| 16 | ЧАСТИЧНО | Legacy ranking + compatibility warnings; полная scoring остаётся. |
| 17 | ЧАСТИЧНО | Inspection domain/service/UI; acceptance позже. |
| 18 | ЧАСТИЧНО | Release acceptance checklist; evidence PENDING. |
| 19 | ЧАСТИЧНО | Legacy parity matrix; строки PENDING. |
| 20 | ЧАСТИЧНО | KB + Системы 1–4 + staging + Review + editor + controlled incomplete Material. Остаются полное сопоставление и UI acceptance. |
| 21 | ЧАСТИЧНО | Source-backed compatibility matrix; каталог не заменяет TDS/НД. |
| 22 | ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ | CompatibilityEngine интегрирован; реальные TDS-backed conditions и UI acceptance остаются. |
| 23 | НЕ ВЫПОЛНЕНО | Pre-Application Check. |
| 24 | НЕ ВЫПОЛНЕНО | Химическая стойкость только через source-backed rules. |
| 25 | ЧАСТИЧНО | Document-level SHA-256 + first rule-level KNOWN promotions with locator/value/applicability. Full normative chain into calculation/UI remains. |
| 26 | НЕ ВЫПОЛНЕНО | Explanation Engine. |
| 27 | ЧАСТИЧНО | Staging, matching, provenance, System Template и controlled incomplete Material реализованы; TDS enrichment/acceptance остаются. |
| 28 | ВЫПОЛНЕНО | Controlled LossProfile. |
| 29 | ЧАСТИЧНО | Catalogue → draft → editor → CONFIRM → persistence; TDS-verified templates gate remains limited by incomplete rule coverage. |
| 30 | ВЫПОЛНЕНО | Engineering Decision Log. |
| 31 | ЧАСТИЧНО | Scenario service/UI + confirmed-template bridge; acceptance remains. |
| 32 | НЕ ВЫПОЛНЕНО | Полный inspection/DFT workflow. |

## Каталог `Системы 1–4`

Файлы в `books/`: `Системы 1.xls`, `Системы 2.XLSX`, `Системы 3.xlsx`, `Системы 4.xlsx`.

Каталог является исходным набором вариантов систем и кандидатов материалов, но не TDS/нормативом. Сохраняются file/sheet/row/SHA-256; неизвестное/неоднозначное = `UNKNOWN`; автоматического доказательства применимости нет.

## Реализованные code stages

- `tds_manifest.py` — `80e75053fc237e4b0c622304f1f502d57050016b`: TDS document/rule verification boundary.
- `spk_effa_tds_catalog.py` — `cc3fb0f57cff584363bb943ae35ed4085dd8019f`: measured binary SHA-256 catalog for 10 SPKEFFA TDS PDFs.
- `tds_rule_promotion.py` — `4a2b23f23255c65de148f840efbe4261731fa375`: explicit promote_tds_rule gate; parse_dft_range_um.
- `tds_known_rules.py` — `1cddff494657dbe754ad76f9f44e192814ad3df0`: first KNOWN rules for Blank Universal and Blank Finish (DFT/solids/density).
- `tds_technology_bridge.py` — `ce0083946158de9b45698eafd1192030db89db39`: check_target_dft_against_known_tds without invented limits.
- `test_spk_effa_tds_catalog.py` — `6b8b426635633a79f28e0408e0c559d9879ecc2c`.
- `test_tds_rule_promotion.py` — `445b726188000a83ba9526fb63c9c59723e81a93`.
- `loss_profile` / calculator / scenario / system template stages — see prior plan entries.

## TDS verification boundary — §12/§14/§25

`kappamaag-crypto/SPKEFFA` — read-only. Git blob SHA-1 ≠ binary PDF SHA-256.

Blank_Universal.pdf:
- binary SHA-256: `9ab3872b849e523652088a3ba0d8b0788005c0134ac517305a9e2f01621b5887`
- Git blob SHA-1: `23eb95f2d327249845ca7ddb5d8b8e116fc2dd3a`

Blank_Finish.pdf binary SHA-256: `34465e17e1e1199c94f1391ca2d776dcd377d4d363e0c4513b4e8a40f7a9a235`

Document KNOWN requires path + binary SHA-256. Rule KNOWN requires explicit promote_tds_rule(document, rule, verified_by=...). Extracted text alone does not promote.

First promoted KNOWN rules:
- BLANK_UNIVERSAL_DFT_RANGE = 80-250 мкм
- BLANK_UNIVERSAL_SOLIDS_BY_VOLUME = 73 ± 2%
- BLANK_UNIVERSAL_DENSITY = 1,4 кг/л
- BLANK_FINISH_DFT_RANGE = 50-90 мкм
- BLANK_FINISH_SOLIDS_BY_VOLUME = 58±3%
- BLANK_FINISH_DENSITY = 1,3 г/см³

## §14/§25 — progress

Done:
- binary SHA-256 document catalog;
- promote gate;
- first KNOWN rules;
- TDS DFT technology bridge for mapped material names.

Still open:
- promote remaining SPKEFFA materials;
- wire bridge into main calculation/UI path;
- template `tds_verified=KNOWN` acceptance based on known rules;
- full normative traceability into EngineeringContext/History.

## §28 / §30 — закрыты ранее

Controlled LossProfile and Engineering Decision Log remain closed.
