# plan2akz — основной план развития АКЗ-калькулятора v3

> **Живой план проекта.** Статус ниже отражает фактическое состояние ветки `v3.0-engineering-upgrade` на 10.09.2026. После каждого существенного этапа статус и evidence обновляются прямо здесь.
>
> **Главный приоритет:** **расчёт АКЗ → система покрытия → проверка → сравнение → Excel/PDF**.
>
> Ключевое требование: система покрытия поддерживает 2, 3, 4 и любое разумное количество слоёв. Legacy Excel на 2 слоя не является ограничением калькулятора v3.

## 0. Правила

1. Не ломать рабочий АКЗ-расчёт.
2. Расчётная логика остаётся в Domain/Service, не в UI.
3. Excel не становится вторым расчётным движком.
4. PDF и Excel получают данные из одного `CalculationResult`/`SystemCalculationResult`.
5. Инженерные и складские данные не смешиваются без необходимости.
6. Каждый существенный этап покрывается тестом/smoke-check.
7. Каждый новый этап — отдельный commit.
8. После commit обновляется этот план.
9. Статус «выполнено» ставится только при наличии фактического кода + теста/CI или явного подтверждённого smoke-check.
10. Отсутствие данных источника означает `UNKNOWN`/«нет подтверждённых данных», а не выдуманный запрет или разрешение.

---

# КОНТРОЛЬНЫЙ АУДИТ 10.09.2026

Текущий рабочий HEAD после отдельного этапа §5: `a1e1a0a1d7fd34c6fee3537dec39e98f13f6281c` (`test: preserve unknown prices in engineering Excel export`). Предыдущий этап §4: `2ad50af7c4de6b0b5ddbb0ef5113dbb023de2d8f`; plan commit после него: `2dbe38d2dcb2bc1d58aaba2ab74a4c86bb967e42`. Этап §3: `42bb7fb282774e6f2c1691557ceba86d77795d21`.

Последовательность последнего блока §22 подтверждена: `bb1d4ef → 1073f9c → c2c795c → 8d2059e → a82d7a7 → 2ba6b0e → 084d989 → a43d5ec → f6354fb → b079786 → 937d633`. CI для каждого нового этапа проверяется отдельно; queued не считается успешным.

Ключевой факт аудита: `upload/app/domain/layer_compatibility.py` существует и проверяет все соседние переходы, а `upload/tests/test_layer_compatibility.py` проверяет engine и `check_result()`. Но `CalculationView` и `SystemsView` не подключают `LayerCompatibilityEngine`; §22 **не закрыт**.

## Матрица §1–§32

| § | Фактический статус | Evidence / факт | Что блокирует закрытие |
|---|---|---|---|
| 1 | **ВЫПОЛНЕНО (core)** | `CalculationService`, multilayer, precision/unit regression | downstream workflow |
| 2 | **ЧАСТИЧНО** | `CalculationView`, `SystemsView`, динамические слои, load/create/copy, UI regression | встроенная compatibility-check + визуальный smoke |
| 3 | **ВЫПОЛНЕНО** | `AdHocMaterialDialog`; normalization, duplicate reuse, ключевые поля, SQLite persistence regression | следующий незакрытый §4 |
| 4 | **ЧАСТИЧНО** | `ComparisonEngine`, `ComparisonView`, multilayer/2K, technology block, comparison Excel; headless UI smoke regression добавлен | фактическая визуальная проверка + финальная проверка формулировок технологических ограничений |
| 5 | **ЧАСТИЧНО** | customer/engineering Excel + regression; добавлен missing-price regression | визуальная проверка, печать/PDF conversion |
| 6 | **ЧАСТИЧНО** | PDF из `SystemCalculationResult`, multilayer/comparison/2K regression | визуальная проверка, печать, Excel↔PDF |
| 7 | **ВЫПОЛНЕНО** | precision/unit invariants + independent 2/3/4/5-layer golden cases + успешные CI | — |
| 8 | **ВЫПОЛНЕНО** | 2K как один mixed-material layer; comparison/Excel/PDF regression | TDS technology rules только в §14 |
| 9 | **НЕ ВЫПОЛНЕНО** | завершённого commercial packaging layer нет | фасовка/комплекты/остаток/резерв/закупка |
| 10 | **ЧАСТИЧНО** | Alembic присутствует | additive strategy + backup/rollback acceptance |
| 11 | **ЧАСТИЧНО** | history/snapshot infrastructure есть | полный immutable snapshot contract |
| 11.1 | **НЕ ВЫПОЛНЕНО** | outbox/SMTP workflow не подтверждён | outbox + retry/backoff + idempotency + safe secrets |
| 12 | **НЕ ВЫПОЛНЕНО** | нормативные документы лежат в `books/` | versioned normative model + traceability |
| 13 | **НЕ ВЫПОЛНЕНО** | источники подготовки поверхности есть | structured Sa/St/profile model |
| 14 | **НЕ ВЫПОЛНЕНО** | часть технологических полей агрегируется в comparison | полноценная TDS-backed validation |
| 15 | **ОТЛОЖЕНО** | OGZ не является текущим P0 core | ПТМ/section factor/R/critical temperature |
| 16 | **ЧАСТИЧНО** | legacy recommendation hard filter/score существует | chemical environment/technology/compatibility/explanation/weights |
| 17 | **НЕ ВЫПОЛНЕНО** | inspection workflow отсутствует | зоны/измерения/project-vs-fact/recoat/repair |
| 18 | **НЕ ВЫПОЛНЕНО** | отдельные regression suites есть | release checklist, smoke, DB, backup/restore, docs |
| 19 | **НЕ ВЫПОЛНЕНО** | legacy sources доступны | capability → v3 → test → UI matrix |
| 20 | **НЕ ВЫПОЛНЕНО** | `books/` содержит источники | indexed KB |
| 21 | **ЧАСТИЧНО** | source-backed compatibility matrix + regression | applicability к реальной химической основе/TDS |
| 22 | **ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ** | `layer_compatibility.py`, `test_layer_compatibility.py`, `check_result()` | подключение к `CalculationView`/`SystemsView`, UI regression, TDS-backed conditions |
| 23 | **НЕ ВЫПОЛНЕНО** | отдельного Pre-Application Check нет | `Подходит / Не подходит / Недостаточно данных` |
| 24 | **НЕ ВЫПОЛНЕНО** | завершённой chemical-environment model нет | source-backed environment rules |
| 25 | **НЕ ВЫПОЛНЕНО** | documents есть | normative traceability model |
| 26 | **НЕ ВЫПОЛНЕНО** | отдельного Explanation Engine нет | explain hard filters/unknown/worst-case/source |
| 27 | **НЕ ВЫПОЛНЕНО** | часть полей Material есть | quality gate + source completeness |
| 28 | **НЕ ВЫПОЛНЕНО** | базовый loss model есть | полноценная source-backed модель потерь |
| 29 | **НЕ ВЫПОЛНЕНО** | saved systems есть | versioned engineering templates |
| 30 | **НЕ ВЫПОЛНЕНО** | decision log отсутствует | воспроизводимый журнал решений |
| 31 | **НЕ ВЫПОЛНЕНО** | scenario layer отсутствует | scenarios поверх `CalculationService` |
| 32 | **НЕ ВЫПОЛНЕНО** | §17 незавершён | полноценный inspection workflow |

**Порядок продолжения:** §4 и §5 остаются частично закрытыми до фактического визуального/печатаемого smoke-check. Следующим по номеру незакрытым пунктом остаётся §5; его automated missing-price regression уже добавлен. После закрытия §5 переходим к §6. §22 остаётся частично закрытым и не может считаться завершённым до интеграции в workflow.

---

# I. ОСНОВНОЙ WORKFLOW АКЗ

## 1. Расчёт АКЗ

**[ВЫПОЛНЕНО — CORE]**

Подтверждены расчёт слоёв, DFT/WFT, теоретический/практический расход, кг/м² и л/м², разбавление, стоимость, площадь, `CalculationResult`/`SystemCalculationResult`, валидация и multi-layer. Precision regression закрыт отдельными invariant/golden tests.

Evidence: `upload/app/services/calculation_service.py`, domain calculator/models, `upload/tests/test_calculation_service_invariants.py`, `test_dilution_v3.py`.

## 2. Система покрытия на основном экране

**[ЧАСТИЧНО]**

Есть динамический редактор 2/3/4+ слоёв, добавление/удаление/перестановка, сохранение порядка, создание черновика из расчёта, копирование системы, SQLite reload и headless Qt regression.

Evidence: `upload/app/ui/views/calculation_view.py`, `systems_view.py`; commits `c00299d…`, `dcdebf1…`, `6f16fd6…`, `7e80e9e…`, `e66d6ca…`, `279b611…`, `3a4c0e4…`, `a192567…`.

До закрытия: сквозной workflow с compatibility check и подтверждённый визуальный smoke-check.

## 3. Материал из экрана расчёта

**[ВЫПОЛНЕНО]**

`+ Материал` сохраняет материал в БД и добавляет его в текущий расчёт. Отдельно подтверждено regression-тестом:
- нормализация имени (`strip` + схлопывание пробелов + `casefold`);
- отсутствие дубля при эквивалентном имени;
- возврат существующего материала вместо создания нового;
- сохранение и SQLite reload ключевых полей: manufacturer, brand, type, binder, density, solids by volume, price/kg, DFT min/max/hard max, 2K flag, active/incomplete;
- корректное сохранение нормализованного имени.

Evidence: `upload/app/ui/dialogs/ad_hoc_material_dialog.py`, `upload/tests/test_ad_hoc_material_dialog.py`, commit `42bb7fb282774e6f2c1691557ceba86d77795d21`.

## 4. Сравнение систем АКЗ

**[ЧАСТИЧНО — SMOKE ДОБАВЛЕН]**

Есть `ComparisonEngine`, сравнение без повторного расчёта, multilayer/2K, запрет смешения площадей, technology block и comparison Excel. Добавлен headless Qt smoke regression, который строит `ComparisonView`, выполняет реальное сравнение 2- и 4-слойной системы и проверяет наличие колонок, multilayer-строк, технологических показателей и доступность экспорта.

Evidence: `upload/app/ui/views/comparison_view.py`, `upload/tests/test_comparison_engine.py`, `upload/tests/test_comparison_regression.py`, `upload/tests/test_comparison_excel_export.py`, `upload/tests/test_comparison_view_smoke.py`, commit `2ad50af7c4de6b0b5ddbb0ef5113dbb023de2d8f`.

Осталось: фактический визуальный smoke-check и финальная проверка формулировок технологических ограничений на реальных карточках. Не менять инженерные значения без подтверждённого источника.

---

# II. EXCEL / PDF

## 5. Excel — customer-facing экспорт

**[ЧАСТИЧНО — MISSING PRICE REGRESSION ДОБАВЛЕН]**

Есть mapping spec, customer/engineering exporters, 2/3/4+ layers, mixed thinner, long names, Commercial/Full, 2K и print settings regression. Добавлен отдельный regression для материала без цены: расчёт не получает выдуманную стоимость, а Excel показывает `—` в инженерных итогах/слоях.

Evidence: `upload/app/infrastructure/export/excel_exporter.py`, `upload/tests/test_comparison_excel_export.py`, `upload/tests/test_excel_missing_price.py`, commit `a1e1a0a1d7fd34c6fee3537dec39e98f13f6281c`.

Осталось: визуальная проверка, реальная печать/PDF conversion.

## 6. PDF — клиентский экспорт

**[ЧАСТИЧНО]** PDF строится из `SystemCalculationResult`, есть multilayer/comparison/long names/unknown price/2K regression. Остались визуальная проверка, печать и Excel↔PDF composition check.

---

# III. РАСЧЁТНЫЙ ДВИЖОК

## 7. Точность / единицы / regression

**[ВЫПОЛНЕНО]** `test_calculation_service_invariants.py` и multilayer golden tests. Commits `8598365345d000c884978642cde4e916c0fbf7a0`, `5662a6f39c6e2312ee30f8bc236a25d8d3c339e9`; CI `34439245472`, `34439280625`, `34440681323` — success.

## 8. 2К материалы

**[ВЫПОЛНЕНО]** 2К — один готовый mixed-material/один слой; A/B не становятся отдельными расчётными позициями. CI `34437813196` и export regression подтверждают это. Pot life/induction остаются §14.

## 9. Фасовка / закупка

**[НЕ ВЫПОЛНЕНО]** Коммерческий слой фасовки/комплектов/остатка/резерва/закупочной стоимости не завершён.

---

# IV. БД / ИСТОРИЯ

## 10. Миграции БД

**[ЧАСТИЧНО]** Alembic присутствует; additive migration + backup/rollback strategy не закрыты acceptance-тестом.

## 11. История / snapshots

**[ЧАСТИЧНО]** Snapshot/history infrastructure есть; полный immutable snapshot contract с порядком слоёв, входами, результатами, версиями и timestamp не закрыт.

## 11.1. Автоматическая синхронизация истории и БД материалов

**[НЕ ВЫПОЛНЕНО]** Нужны outbox, background SMTP, retry/backoff, idempotency и safe secrets. SQLite остаётся source of truth.

---

# V. ИНЖЕНЕРНЫЕ ДАННЫЕ АКЗ

## 12. Среда / ISO 12944 / ГОСТ

**[НЕ ВЫПОЛНЕНО]** `books/` содержит ГОСТ 34667/ISO 12944, но versioned normative model не завершена.

## 13. Подготовка поверхности

**[НЕ ВЫПОЛНЕНО]** Источники есть, структурированной модели Sa/St/profile/standard нет.

## 14. Технологические условия

**[НЕ ВЫПОЛНЕНО]** Comparison агрегирует часть технологических полей, но полноценной TDS-backed validation нет.

## 15. Огнезащита OGZ

**[ОТЛОЖЕНО]** После стабилизации АКЗ core.

---

# VI. RECOMMENDATION / QUALITY

## 16. Recommendation Engine

**[ЧАСТИЧНО]** Legacy hard filter/score существуют. Не закрыто: chemical environment, technology, compatibility, explanation и configurable weights.

## 17. Контроль качества / фактический DFT

**[НЕ ВЫПОЛНЕНО]** Нет завершённого inspection workflow.

## 18. Release / regression / документация

**[НЕ ВЫПОЛНЕНО]** Нужны полный regression, application smoke, golden АКЗ/Excel/PDF, DB backup/restore, docs и release checklist.

---

# VII. РАСШИРЕНИЕ ИНЖЕНЕРНОГО ROADMAP

## 19. Legacy parity audit — P1

**[НЕ ВЫПОЛНЕНО]** Матрица capability → v3 → status → test → UI не составлена.

## 20. Knowledge Base из `books/` — P1

**[НЕ ВЫПОЛНЕНО]** Нужны source/version/section/rule/applicability/limitations/link/date.

## 21. Совместимость ЛКМ — P1

**[ЧАСТИЧНО]** Source-backed matrix с направлением `previous → applied`, `+`, `1`, `2`, `UNKNOWN` реализована и протестирована. Не сделаны необоснованные автоматические выводы для неоднозначных binder families.

Evidence commits: `bb1d4ef07cf7c314fe5e3e770b988a7ffcac5a7e`, `1073f9c337d94a2dd7adce30d4190f07dbf74491`, `8d2059eb39fa2bf46e0fc69f3855abf6b3f60584`.

## 22. Layer Compatibility Engine — P1

**[ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ]**

`upload/app/domain/layer_compatibility.py` проверяет каждый соседний переход для любого числа слоёв и умеет проверять уже рассчитанный `SystemCalculationResult` без повторного расчёта. `upload/tests/test_layer_compatibility.py` покрывает multilayer, warning `2`, UNKNOWN, worst-case, context count и `check_result()`.

Evidence: `2ba6b0e0ad73c953ee194c87bba8266857f1520e`, `002bbe65e979c1b9e2dc9d807ec9ab4972497b20`, `f6354fb4b6cdcdc30c33a4640e8c5e3a8f47e13d`, `b079786ecae4605fd8ed580bbab4930875e72b57`, docs `937d6334b4bf1bb2ea88ec5bc5ff43f9d87f3bc1`.

Осталось:
1. подключить engine непосредственно к editor систем и основному workflow `CalculationView`/`SystemsView`;
2. показывать warning/blocking information без изменения расчёта расхода;
3. добавить TDS-backed `previous_is_cured`, `recoat_elapsed_h`, `surface_prepared` только там, где правило подтверждено TDS/официальной документацией;
4. отсутствие данных не превращать в запрет;
5. UI regression на реальный пользовательский маршрут.

## 23. Pre-Application Check / технологическая готовность — P1

**[НЕ ВЫПОЛНЕНО]** Единая проверка условий нанесения с результатом `Подходит / Не подходит / Недостаточно данных`.

## 24. Химическая стойкость и среда эксплуатации — P1

**[НЕ ВЫПОЛНЕНО]** Только source-backed environment rules.

## 25. Нормативная traceability — P1

**[НЕ ВЫПОЛНЕНО]** Нужна модель нормативного документа/правила с версией, пунктом и применением.

## 26. Explanation Engine — P1

**[НЕ ВЫПОЛНЕНО]** Объясняет уже рассчитанное решение, но не принимает инженерное решение самостоятельно.

## 27. Material Data Quality — P1

**[НЕ ВЫПОЛНЕНО]** Quality gate полноты карточки и источников критических параметров.

## 28. Loss Profile — P1

**[НЕ ВЫПОЛНЕНО]** Управляемая source-backed модель потерь без изменения базовой формулы без regression/golden.

## 29. System Templates — P2

**[НЕ ВЫПОЛНЕНО]** Versioned engineering templates для 2/3/4+ layers.

## 30. Engineering Decision Log — P2

**[НЕ ВЫПОЛНЕНО]** Воспроизводимый журнал входов, filters, исключений, rules, sources и versions.

## 31. Calculation Scenarios — P2

**[НЕ ВЫПОЛНЕНО]** Сценарии поверх существующего `CalculationService`/result models.

## 32. Inspection / фактический DFT workflow — P2

**[НЕ ВЫПОЛНЕНО]** Зоны, измерения, проект/факт, соответствие, repair/recoat, фото/акты.

---

# ПРОТОКОЛ РАБОТЫ С ПЛАНОМ

- Сначала закрываем **первый реально незакрытый §** по номеру.
- §22 не считать закрытым до фактической интеграции в `CalculationView`/`SystemsView` и TDS-backed правил.
- Не закрывать этап только по наличию файла или старой записи в плане; требуется сопоставление `код → тест → commit → CI/smoke`.
- Каждый новый этап: отдельный commit; после него отдельная запись в этом плане.
- Для §4 headless smoke не заменяет фактическую визуальную проверку.
- Для §5 missing-price regression не заменяет визуальную проверку и реальную печать/PDF conversion.
