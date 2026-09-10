# plan2akz — основной план развития АКЗ-калькулятора v3

> **Живой план проекта.** Статус ниже отражает фактическое состояние ветки `v3.0-engineering-upgrade` на 10.09.2026, а не старые предположения. После каждого существенного этапа статус и evidence обновляются прямо здесь.
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

Текущий HEAD: `937d6334b4bf1bb2ea88ec5bc5ff43f9d87f3bc1` (`docs: record calculation-result compatibility check`). Последние commits по §22 действительно существуют и идут цепочкой `bb1d4ef → 1073f9c → c2c795c → 8d2059e → a82d7a7 → 2ba6b0e → 084d989 → a43d5ec → f6354fb → b079786 → 937d633`. Текущий CI для HEAD `34449700058` находится в состоянии `queued`; поэтому он не считается подтверждением закрытия этапа.

Ключевой факт аудита: `upload/app/domain/layer_compatibility.py` существует и проверяет все соседние переходы, а `upload/tests/test_layer_compatibility.py` проверяет engine и `check_result()`. Но `CalculationView` и `SystemsView` в текущем коде не подключают `LayerCompatibilityEngine`; значит §22 **не закрыт** и нельзя считать проверку частью пользовательского workflow.

## Матрица §1–§32

| § | Фактический статус | Что подтверждено | Что блокирует закрытие |
|---|---|---|---|
| 1 | **ВЫПОЛНЕНО (core)** | `CalculationService`, multi-layer, precision/unit regression | downstream workflow закрывается последующими § |
| 2 | **ЧАСТИЧНО** | `CalculationView`, `SystemsView`, динамические слои, загрузка/создание/копирование, UI regression | нет сквозной встроенной проверки совместимости; визуальный smoke-check также не подтверждён |
| 3 | **ЧАСТИЧНО** | `AdHocMaterialDialog`, нормализация имени, duplicate check, сохранение и авто-добавление в расчёт | нет отдельного regression на normalization + все поля + SQLite reload/restart |
| 4 | **ЧАСТИЧНО** | `ComparisonEngine`, `ComparisonView`, multilayer comparison, technology block, comparison Excel | визуальный smoke-check и финальная проверка формулировок на реальных карточках не подтверждены |
| 5 | **ЧАСТИЧНО** | customer Excel, engineering Excel, multilayer/2K regression | визуальный customer-facing контроль, реальная печать/PDF conversion и финальная проверка missing prices |
| 6 | **ЧАСТИЧНО** | PDF из `SystemCalculationResult`, multilayer/2K/comparison regression | визуальная проверка, печать и Excel↔PDF состав |
| 7 | **ВЫПОЛНЕНО** | precision/unit invariants, independent 2/3/4/5-layer golden cases, CI successes | нет незакрытого core-пункта |
| 8 | **ВЫПОЛНЕНО** | 2K как один mixed-material layer; comparison/Excel/PDF regression | технологические ограничения — только через §14/TDS |
| 9 | **НЕ ВЫПОЛНЕНО** | отдельного завершённого коммерческого слоя фасовки нет | фасовка/банки/комплекты/остаток/резерв/закупка |
| 10 | **ЧАСТИЧНО** | Alembic присутствует | additive strategy + backup/rollback не доведены до подтверждённого этапа |
| 11 | **ЧАСТИЧНО** | snapshot/history infrastructure присутствует | полный immutable snapshot с версией формул/приложения/временем не закрыт как acceptance stage |
| 11.1 | **НЕ ВЫПОЛНЕНО** | outbox/SMTP workflow не подтверждён | outbox + retry/backoff + idempotency + safe secrets |
| 12 | **НЕ ВЫПОЛНЕНО** | нормативные книги лежат в `books/` | версионируемая нормативная domain-модель + traceability |
| 13 | **НЕ ВЫПОЛНЕНО** | источники по подготовке поверхности есть в `books/` | структурированная модель Sa/St/профиля/ГОСТ/ISO |
| 14 | **НЕ ВЫПОЛНЕНО** | отдельные технологические значения уже используются в comparison | полноценная технологическая валидация по подтверждённым TDS |
| 15 | **ОТЛОЖЕНО** | OGZ не является текущим P0 core | ПТМ/section factor/R/critical temperature после стабилизации АКЗ |
| 16 | **ЧАСТИЧНО** | legacy recommendation engine существует | chemical environment + technology + compatibility + explanation + configurable weights |
| 17 | **НЕ ВЫПОЛНЕНО** | фактический DFT workflow отсутствует | зоны, измерения, проект/факт, repair/recoat |
| 18 | **НЕ ВЫПОЛНЕНО** | отдельные regression suites есть | полный release checklist, smoke, DB, backup/restore, golden exports/docs |
| 19 | **НЕ ВЫПОЛНЕНО** | legacy исходники/история доступны | матрица legacy capability → v3 → test → UI |
| 20 | **НЕ ВЫПОЛНЕНО** | `books/` содержит исходные документы | индексируемая KB с источником/версией/пунктом/правилом |
| 21 | **ЧАСТИЧНО** | source-backed compatibility matrix + regression; `+`, `1`, `2`, `UNKNOWN`; направленность `previous → applied` | производитель/TDS applicability ещё не подтверждены для каждой пары |
| 22 | **ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ** | `layer_compatibility.py`, `test_layer_compatibility.py`, `check_result()` | подключить engine к editor/main workflow; TDS-backed cure/recoat/surface rules только при наличии подтверждённого источника; UI warning без изменения расчёта |
| 23 | **НЕ ВЫПОЛНЕНО** | отдельного Pre-Application Check нет | единый результат Подходит/Не подходит/Недостаточно данных |
| 24 | **НЕ ВЫПОЛНЕНО** | химическая стойкость не имеет завершённой domain-модели | source-backed environment rules |
| 25 | **НЕ ВЫПОЛНЕНО** | документы есть | `NormativeDocument/NormativeRule` или эквивалент + traceability |
| 26 | **НЕ ВЫПОЛНЕНО** | отдельного Explanation Engine нет | объяснение hard filters/unknown/worst-case/source |
| 27 | **НЕ ВЫПОЛНЕНО** | material model содержит часть полей | quality gate полноты инженерных данных и источников |
| 28 | **НЕ ВЫПОЛНЕНО** | базовый `LossProfile` существует/участвует в расчёте | полноценная source-backed управляемая модель потерь |
| 29 | **НЕ ВЫПОЛНЕНО** | сохранённые системы уже есть | отдельные versioned system templates |
| 30 | **НЕ ВЫПОЛНЕНО** | полноценного decision log нет | воспроизводимый журнал решений, источников и версий |
| 31 | **НЕ ВЫПОЛНЕНО** | отдельного сценарного слоя нет | сценарии поверх существующего `CalculationService` |
| 32 | **НЕ ВЫПОЛНЕНО** | §17 остаётся незавершённым | полноценный inspection workflow |

**Порядок продолжения после аудита:** строго по первому незакрытому пункту. Поэтому следующим является **§3**, а не §22 и не новые P1/P2 пункты. §22 остаётся явно частично закрытым до интеграции в workflow.

---

# I. ОСНОВНОЙ WORKFLOW АКЗ — КРИТИЧЕСКИЙ ПРИОРИТЕТ

## 1. Расчёт АКЗ

**[ВЫПОЛНЕНО — CORE]**

Подтверждены расчёт слоёв, DFT/WFT, теоретический/практический расход, кг/м² и л/м², разбавление, стоимость, площадь, `CalculationResult`/`SystemCalculationResult`, валидация и multi-layer расчёт. Precision/regression покрывает отсутствие промежуточного округления, кг/л, площадь и разные основания разбавления.

Evidence: `upload/app/services/calculation_service.py`, domain calculator/models, `upload/tests/test_calculation_service_invariants.py`, `test_dilution_v3.py`; CI ранее подтверждал regression.

## 2. Система покрытия на основном экране

**[ЧАСТИЧНО]**

Есть динамический редактор 2/3/4+ слоёв, добавление/удаление/перестановка, сохранение порядка, создание черновика из расчёта, копирование сохранённой системы, SQLite reload и headless Qt regression.

Evidence: `upload/app/ui/views/calculation_view.py`, `systems_view.py`, UI regression; commits `c00299d…`, `dcdebf1…`, `6f16fd6…`, `7e80e9e…`, `e66d6ca…`, `279b611…`, `3a4c0e4…`, `a192567…`.

До закрытия: сквозной workflow должен включать проверку совместимости, а визуальный smoke-check должен быть отдельно подтверждён.

## 3. Материал из экрана расчёта

**[ЧАСТИЧНО — СЛЕДУЮЩИЙ ЭТАП]**

`+ Материал` уже сохраняет материал в БД и добавляет его в текущий расчёт. `AdHocMaterialDialog._normalize_name()` и duplicate check существуют, но отдельного regression на normalization, все пользовательские поля и сохранность после SQLite reload/restart в текущей ветке не найдено.

Evidence: `upload/app/ui/dialogs/ad_hoc_material_dialog.py`, `upload/app/ui/views/calculation_view.py`. Не найден `upload/tests/test_ad_hoc_material_dialog.py`.

**Следующий этап:** добавить regression, не менять расчётный движок. Acceptance: `"  Material   X "`, `"material x"` и эквивалентные пробельные варианты не создают дубль; существующий материал возвращается; manufacturer/brand/type/binder/density/solids/price/DFT/component flag сохраняются и восстанавливаются из SQLite; новый материал автоматически попадает в текущий расчёт.

## 4. Сравнение систем АКЗ

**[ЧАСТИЧНО]**

Есть `ComparisonEngine`, сравнение без повторного расчёта, multilayer/2K, запрет смешения площадей, technology block и comparison Excel.

Evidence: `upload/tests/test_comparison_engine.py`, `test_comparison_regression.py`, `test_comparison_excel_export.py`. До закрытия: визуальный smoke-check и проверка формулировок технологических ограничений на реальных карточках.

---

# II. EXCEL / PDF

## 5. Excel — customer-facing экспорт

**[ЧАСТИЧНО]**

Есть `docs/plan2akz_excel_mapping.md`, customer/engineering exporters, 2/3/4+ layers, mixed thinner, long names, Commercial/Full, 2K, print settings regression. Не считать этап полностью закрытым до визуальной проверки, реальной печати/PDF conversion и проверки missing prices.

## 6. PDF — клиентский экспорт

**[ЧАСТИЧНО]**

Есть PDF из `SystemCalculationResult`, multilayer/comparison/long names/unknown price и 2K regression. Остались визуальная проверка, печать и Excel↔PDF composition check.

---

# III. РАСЧЁТНЫЙ ДВИЖОК

## 7. Точность / единицы / regression

**[ВЫПОЛНЕНО]**

Evidence: `test_calculation_service_invariants.py`, multilayer golden tests; commits `8598365345d000c884978642cde4e916c0fbf7a0`, `5662a6f39c6e2312ee30f8bc236a25d8d3c339e9`; CI `34439245472`, `34439280625`, `34440681323` — success.

## 8. 2К материалы

**[ВЫПОЛНЕНО]**

2К — один готовый mixed-material/один слой; A/B не становятся отдельными расчётными позициями. Evidence: multilayer 2K CI `34437813196` и export regression. Pot life/induction остаются технологической валидацией §14.

## 9. Фасовка / закупка

**[НЕ ВЫПОЛНЕНО]**

Коммерческий слой фасовки/количества комплектов/остатка/резерва/закупочной стоимости пока не завершён и не должен проникать в engineering export.

---

# IV. БД / ИСТОРИЯ

## 10. Миграции БД

**[ЧАСТИЧНО]** Alembic присутствует; additive migration + backup/rollback strategy не закрыты acceptance-тестом.

## 11. История / snapshots

**[ЧАСТИЧНО]** Snapshot/history infrastructure есть; полный immutable snapshot contract с порядком слоёв, входами, результатами, версиями и timestamp ещё не закрыт.

## 11.1. Автоматическая синхронизация истории и БД материалов

**[НЕ ВЫПОЛНЕНО]** Требуются локальный outbox, background SMTP, retry/backoff, idempotency и безопасные secrets. SQLite остаётся source of truth.

---

# V. ИНЖЕНЕРНЫЕ ДАННЫЕ АКЗ

## 12. Среда / ISO 12944 / ГОСТ

**[НЕ ВЫПОЛНЕНО]** `books/` содержит ГОСТ 34667/ISO 12944, но нет завершённой versioned normative model.

## 13. Подготовка поверхности

**[НЕ ВЫПОЛНЕНО]** Источники есть в `books/`, структурированной модели Sa/St/profile/standard пока нет.

## 14. Технологические условия

**[НЕ ВЫПОЛНЕНО]** Comparison уже агрегирует часть технологических полей, но полноценного Pre-Application/production validation нет. TDS-backed значения не должны заменяться догадками.

## 15. Огнезащита OGZ

**[ОТЛОЖЕНО]** После стабилизации АКЗ core.

---

# VI. RECOMMENDATION / QUALITY

## 16. Recommendation Engine

**[ЧАСТИЧНО]** Legacy hard filter/score существуют. Не закрыто: chemical environment, technology, compatibility, explanations и configurable weights.

## 17. Контроль качества / фактический DFT

**[НЕ ВЫПОЛНЕНО]** Нет завершённого inspection workflow.

## 18. Release / regression / документация

**[НЕ ВЫПОЛНЕНО]** Нужны полный regression, application smoke, golden АКЗ/Excel/PDF, DB backup/restore, docs и release checklist.

---

# VII. РАСШИРЕНИЕ ИНЖЕНЕРНОГО ROADMAP

## 19. Legacy parity audit — P1

**[НЕ ВЫПОЛНЕНО]** Нужна матрица capability → v3 → status → test → UI. Переносится возможность, а не legacy architecture.

## 20. Knowledge Base из `books/` — P1

**[НЕ ВЫПОЛНЕНО]** Нужны source/version/section/rule/applicability/limitations/source link/date-of-validity.

## 21. Совместимость ЛКМ — P1

**[ЧАСТИЧНО]**

Подтверждена source-backed матрица с направлением `previous → applied`, `+`, `1`, `2`, `UNKNOWN`. Реализованы `upload/app/domain/compatibility.py` и regression. Не делаются автоматические выводы для алкидов/цинк-этилсиликата и других неоднозначных семейств.

Evidence commits: `bb1d4ef07cf7c314fe5e3e770b988a7ffcac5a7e`, `1073f9c337d94a2dd7adce30d4190f07dbf74491`, `8d2059eb39fa2bf46e0fc69f3855abf6b3f60584`.

## 22. Layer Compatibility Engine — P1

**[ЧАСТИЧНО — НЕ ЗАКРЫВАТЬ]**

`upload/app/domain/layer_compatibility.py` проверяет каждый соседний переход для любого числа слоёв и умеет принимать уже рассчитанный `SystemCalculationResult` без повторного расчёта. `upload/tests/test_layer_compatibility.py` покрывает multilayer, warning `2`, UNKNOWN, worst-case, context count и `check_result()`.

Evidence commits: `2ba6b0e0ad73c953ee194c87bba8266857f1520e`, `002bbe65e979c1b9e2dc9d807ec9ab4972497b20`, `f6354fb4b6cdcdc30c33a4640e8c5e3a8f47e13d`, `b079786ecae4605fd8ed580bbab4930875e72b57`, documentation commit `937d6334b4bf1bb2ea88ec5bc5ff43f9d87f3bc1`.

**Осталось:**
1. подключить engine непосредственно к editor систем и основному workflow `CalculationView`/`SystemsView`;
2. показывать результат проверки как warning/blocking information, не изменяя расчёт расхода;
3. добавить TDS-backed `previous_is_cured`, `recoat_elapsed_h`, `surface_prepared` только для материалов, где соответствующее правило подтверждено TDS/официальной документацией;
4. не превращать отсутствие данных в запрет;
5. добавить UI regression на реальный workflow.

## 23. Pre-Application Check / технологическая готовность — P1

**[НЕ ВЫПОЛНЕНО]** Единая проверка условий нанесения и результат `Подходит / Не подходит / Недостаточно данных`.

## 24. Химическая стойкость и среда эксплуатации — P1

**[НЕ ВЫПОЛНЕНО]** Только source-backed rules; никаких выводов по одному названию смолы.

## 25. Нормативная traceability — P1

**[НЕ ВЫПОЛНЕНО]** Нужна модель нормативного документа/правила с версией, пунктом и применённым правилом.

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

**[НЕ ВЫПОЛНЕНО]** Сценарии поверх того же `CalculationService`/result models.

## 32. Inspection / фактический DFT workflow — P2

**[НЕ ВЫПОЛНЕНО]** Зоны, измерения, проект/факт, соответствие, repair/recoat, фото/акты.

---

# ПРОТОКОЛ РАБОТЫ С ПЛАНОМ

- Сначала закрываем **первый реально незакрытый §** по номеру.
- Для текущего состояния это **§3**.
- После реализации §3: отдельный commit с кодом/тестом, затем отдельный commit обновления этого плана (если изменение плана не включено в тот же строго выделенный этап — не смешивать этапы).
- §22 не считать закрытым до фактической интеграции в `CalculationView`/`SystemsView` и TDS-backed правил.
- Не закрывать этап только по наличию файла или старой записи в плане; требуется сопоставление `код → тест → commit → CI/smoke`.
- Текущий CI `34449700058` на HEAD `937d6334…` находится в `queued` и не используется как доказательство успеха.
