# Этап 3. План миграции старой версии

## Цели миграции

1. Не потерять ни одного материала из старой `coatings.db`
2. Не потерять шаблоны систем
3. Перенести историю расчётов и сравнений из JSON в SQLite
4. Сохранить обратную совместимость формул
5. Создать резервные копии перед любым изменением

## Источники данных

| Источник | Формат | Что содержит |
|----------|--------|--------------|
| `coatings.db` | SQLite | Материалы + растворители + шаблоны + history изменений |
| `calculation_history.json` | JSON | История расчётов |
| `comparison_history.json` | JSON | История сравнений |
| `КалькуляторЭКСЕЛЛЬ.xlsx` | Excel | Примеры систем (для seed) |

## Шаги миграции

### Шаг 1. Резервное копирование
- Копировать `coatings.db` → `data/backups/coatings_YYYYMMDD_HHMMSS.db`
- Копировать JSON-истории

### Шаг 2. Создание новой схемы
- Создать все таблицы новой БД (см. database/models.py)

### Шаг 3. Импорт материалов
```
старая coatings → новая materials
```
Маппинг полей:
- name → material_name
- binder → binder_type
- density → density
- solid_content → solids_percent
- price_kg → price_per_kg
- price_liter → price_per_liter
- is_thinner → material_type = THINNER / обычный

Дополнительно:
- manufacturer = "Не указан" (если отсутствует)
- material_type определяется по имени/связующему (эвристика + ручная проверка)

### Шаг 4. Импорт шаблонов
```
coating_templates + template_layers → coating_systems + coating_system_layers
```

### Шаг 5. Импорт истории расчётов
JSON → таблицы `calculations` + `calculation_layers`

### Шаг 6. Отчёт миграции
Показать пользователю:
- Сколько материалов перенесено
- Сколько дублей найдено
- Сколько записей требуют ручной доразметки (категории C, DFT и т.д.)
- Список материалов с неполными данными

### Шаг 7. Режим «только чтение» старых данных
Старые JSON и старая БД не удаляются автоматически.

## Риски и меры

| Риск | Мера |
|------|------|
| Потеря данных | Обязательный backup + dry-run режим |
| Дубликаты | Проверка по name + manufacturer |
| Неполные данные | Пометка `is_incomplete=True` + отчёт |
| Изменение формул | Unit-тесты, сравнивающие результаты со старым калькулятором |

## Актуальная расширенная база материалов v3

Помимо исторической coatings.db, проект теперь использует master-каталог из пяти Excel-источников:

- books/Системы 1.xls
- books/Системы 2.XLSX
- books/Системы 3.xlsx
- books/Системы 4.xlsx
- books/Таблица на 1 кв.м ЛКМ основная.xlsx

Генератор: upload/scripts/build_material_catalog.py.

Для всех пяти Excel-источников поле «Сухой остаток» означает **объёмный сухой остаток (%)** и сохраняется только в solids_by_volume_percent. В solids_percent эти значения не копируются.

Полный master импортируется в materials при запуске приложения. Дубли специально не удаляются автоматически: пользователь может выполнить ручную чистку после первоначального импорта. Повторный запуск не восстанавливает вручную удалённые записи того же master-каталога, поскольку импорт фиксируется по SHA-256 каталога.

Для Windows без GitHub Actions доступен локальный запуск:

```powershell
.\upload\scripts\rebuild_material_catalog.ps1
```

Результаты генератора: upload/data/material_catalog_master_v3.json, upload/data/material_catalog_master_v3.csv, upload/data/material_catalog_review_candidates_v3.csv.
