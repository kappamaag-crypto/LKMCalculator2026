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
| 12 | ЧАСТИЧНО | Engineering context/source identity/History/verified loader; реальные rules ещё не подтверждены. |
| 13 | ЧАСТИЧНО | Surface preparation/profile/condition + UI; acceptance позже. |
| 14 | НЕ ВЫПОЛНЕНО | TDS-backed technological validation из SPKEFFA read-only. |
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
| 25 | НЕ ВЫПОЛНЕНО | Полная normative traceability. |
| 26 | НЕ ВЫПОЛНЕНО | Explanation Engine. |
| 27 | ЧАСТИЧНО | Staging, matching, provenance, System Template и controlled incomplete Material реализованы; TDS enrichment/acceptance остаются. |
| 28 | ВЫПОЛНЕНО | Controlled LossProfile: domain model + integration into SystemCalculator/LayerInput; explicit losses_percent priority over profile; LossProfile.none(); no hidden engineering defaults; regression tests in test_loss_profile.py. Commits: eac21b6 (model), d93f48e (integration), 3e3873f (tests). |
| 29 | ЧАСТИЧНО | Catalogue → draft → editor → explicit CONFIRM → persistence boundary реализовано; persistence блокирует UNKNOWN TDS. Scenario UI подключён, а источник альтернатив ограничен подтверждёнными и TDS-verified templates. Persistence/acceptance остаются. |
| 30 | ВЫПОЛНЕНО | Engineering Decision Log создан: `docs/engineering_decision_log_v3.md`. Зафиксированы границы domain/service, единый calculation result для PDF/Excel, семантика UNKNOWN, read-only SPKEFFA, catalogue vs TDS proof, CONFIRM gate, controlled LossProfile, TDS promotion gate и запрет GitHub Actions. Commit: 9005c30. |
| 31 | ЧАСТИЧНО | `CalculationScenario` + `CalculationScenarioService` + UI подключены к существующему `CalculationService`; Comparison/Excel workflow используется без второго расчётного движка. Добавлен read-only bridge confirmed + `tds_verified=KNOWN` templates → scenario alternatives. Acceptance остаётся. |
| 32 | НЕ ВЫПОЛНЕНО | Полный inspection/DFT workflow. |

## Каталог `Системы 1–4`

Файлы в `books/`: `Системы 1.xls`, `Системы 2.XLSX`, `Системы 3.xlsx`, `Системы 4.xlsx`.

Каталог является исходным набором вариантов систем и кандидатов материалов, но не TDS/нормативом. Сохраняются file/sheet/row/SHA-256; неизвестное/неоднозначное = `UNKNOWN`; автоматического доказательства применимости нет.

## Реализованные code stages

- `book_content_index.py` — `047839b0df403f8ae552394110408b15d219a8c6`: индекс XLS/XLSX и locator `sheet:<лист>!row:<номер>`.
- `system_catalog_importer.py` — `d7fa8f5af2b160da8153fe0bf6d93cbfcb527aae`: review-first staging, candidates, provenance, duplicate normalization.
- `xlrd` — `ff1142c35d09c8b10d3aa708a06cb5576de38563`: legacy XLS reader dependency.
- `system_catalog_review_view.py` — `43257fbbbff67fb206b164c5b64baaa0ee347748`: базовый Review/Staging UI.
- `system_template.py` — `d01b0244d46a84e321517a00fe88ed22c3d22187`: immutable draft model/statuses/DFT/provenance.
- `system_template_service.py` — `5d610e30669d7842598b74ced9049ce433827af9`: draft builder, DB matching, `can_confirm`.
- `system_template_models.py` — `127486c04e6a4a06d92d429c943a188ea7fb1eb1`: ORM tables.
- `system_template_repository.py` — `b180e757c688eee8ce7e2f9ff083bc524c218108`: persistence repository boundary.
- `007_system_templates.py` — `75b394567d64bbc33f1f8871e503c5f79c46c6b6`: Alembic schema.
- `engine.py` — `cb2d6cc7afe2e6a45ee780be4dd7888eea8dbcb5`: ORM registration.
- `system_template_persistence_service.py` — `da6d542c2a3c1557401ccfcf699b2bdcb42a9e56`: explicit CONFIRMED persistence; requires `tds_verified=KNOWN`.
- `main_window.py` — `c960d9ea6e52f74f46b10a91193c31adbcb6f83b`: catalogue tab/menu and material refresh.
- `system_template_editor_view.py` — `845be44fdbbd6417112cb89e9804b758894e1a3d`: draft editor, manual Material selection, explicit CONFIRM gate.
- `system_catalog_review_view.py` — `8b68ce1de37c39608d73a4d2a1699d275aaf4ebb`: selected row → draft/editor, controlled incomplete Material creation, CONFIRM → persistence wiring.
- `tds_manifest.py` — `80e75053fc237e4b0c622304f1f502d57050016b`: explicit TDS document/rule verification boundary; extracted PDF text is not promoted automatically.
- `calculation_scenario.py` — `f301f2ae08c65c5d230c91877a48f4470658f3e3`: immutable scenario boundary with named alternatives and shared object/context.
- `calculation_scenario_service.py` — `1623aee6e51c211191fb786a4f9ecbeb0e1fc4b6`: initial scenario orchestration; repeated-material validation fixed in `b36573abf795c1b13ba6706de6c9beb57c227816`.
- `calculation_scenario_view.py` — `afc098441ad23130204377c8e2230330daebe8a8`: scenario UI with shared-object alternatives, result table and handoff to Comparison.
- `main_window.py` — `ed2b1462cd03a7c09b9f5717660e471bb73cd4bb`: scenario service/view integration and engineering-context propagation.
- `comparison_view.py` — `ce02fb4d2f07411e3575ad6156a1497e6c22b9a8`: public `clear()` boundary for scenario handoff.
- `calculation_scenario_view.py` — `2657a414825046419d376d263574736a51af662f`: scenario uses public Comparison clear API.
- `confirmed_system_template_service.py` — `09a6e732ff0744e200dd156904a877670d6ec27c`: read-only bridge that exposes only CONFIRMED + `tds_verified=KNOWN` templates with complete source/material/DFT data.
- `main_window.py` — `047379bfaefb995b93e5e644bdbcdbf1d891b66e`: scenario alternatives now come only from confirmed, TDS-verified templates; ordinary catalogue systems are not promoted into scenarios.
- `loss_profile.py` — `eac21b6df1b7989961740ec3a36f3a6dd3a0f36c`: controlled LossProfile domain model (name/percent/source, resolve, none()).
- `calculator.py` — `d93f48e3ff999c802457d1e842f23848c37edbcb`: LossProfile integrated into SystemCalculator/LayerInput; explicit losses_percent priority; legacy default_losses preserved as 0.0 without hidden engineering values.
- `test_loss_profile.py` — `3e3873fc9445d87694433be93701e5ed772fd27c`: regression coverage for profile usage, explicit override, none(), invalid rejection, legacy compatibility.
- `engineering_decision_log_v3.md` — `9005c30b453ed2f23ef40f585adddebe5ae13818`: Engineering Decision Log for v3; factual architectural and engineering decisions recorded without promoting UNKNOWN data to KNOWN.

## §20/§27/§29/§31 — следующий шаг

1. Проверить фактическую структуру каждого листа/строки; не угадывать заголовки.
2. Сохранить/показать однозначные DB matches.
3. Для отсутствующего материала использовать только явное создание incomplete Material; неизвестные поля не заполнять.
4. Для неоднозначного match — ручной выбор.
5. Редактор draft реализован.
6. CONFIRM — отдельное действие.
7. CONFIRM → persistence wiring реализован, но `tds_verified=KNOWN` обязателен.
8. Scenario domain/service/UI реализованы; bridge к confirmed System Templates готов и безопасно отбрасывает UNKNOWN/incomplete templates.
9. Следующий инженерный блок — реальная TDS verification из `SPKEFFA` (§14/§25), после чего появятся первые допустимые confirmed-template alternatives. Затем — acceptance сценария/сравнения/экспорта.

## TDS verification boundary — §12/§14/§25

`kappamaag-crypto/SPKEFFA` используется только read-only. Git blob SHA-1 не является SHA-256 бинарного PDF. Для `KNOWN` нужны реальный SHA-256 PDF, явный source identity, locator и applicability правила. Пока бинарные SHA-256 и rule-by-rule verification не внесены, технологические ограничения остаются `UNKNOWN`.

## §28 — Controlled LossProfile (закрыто)

Приоритет разрешения потерь:
1. явный `losses_percent` (включая 0.0);
2. `LayerInput.loss_profile` или `SystemCalculator.loss_profile`;
3. legacy `default_losses` (по умолчанию 0.0 — не скрытое инженерное значение).

`LossProfile.none()` — явный нулевой профиль (`source=SYSTEM`). Некорректный percent отклоняется. Существующий API `LayerCalculator.calculate(..., losses_percent=0.0)` сохранён.

## §30 — Engineering Decision Log (закрыто)

`docs/engineering_decision_log_v3.md` фиксирует фактически принятые архитектурные решения и границы доверия к данным. Отдельная запись не повышает статус TDS rules: `UNKNOWN` остаётся `UNKNOWN` до выполнения §14/§25.
