# Этап 1. Аудит существующего проекта LKMCalculator2026

Дата аудита: 2026-09-08

## Исходные файлы

| Файл | Размер | Назначение |
|------|--------|------------|
| `КалькуляторЭКСЕЛЛЬ.xlsx` | 15 КБ | Простой Excel-калькулятор расхода |
| `Формулы_и_определения.txt` | 878 байт | Справочник формул |
| `Calv1Grah.py` | ~6490 строк | Первая версия Tkinter-калькулятора |
| `Calv1Grah1.py` | ~6599 строк | Улучшенная версия (type hints) |

## Что уже реализовано и работает

### GUI (Tkinter)
- Главное окно расчёта с таблицей слоёв
- Диалоги: история расчётов, история сравнений, база материалов, шаблоны, сравнение систем
- Combobox с поиском
- Предпросмотр и выборочный экспорт

### База данных (SQLite)
- Таблица `coatings` (материалы + растворители)
- Таблицы шаблонов `coating_templates` + `template_layers`
- История изменений материалов (add/update/delete history)

### Расчётный движок
- Полный пересчёт слоя в `update_layer_calculations`
- Расчёт разбавителей/растворителей
- Итоговые суммы по системе (толщина, расход кг/л, стоимость)

### История
- `calculation_history.json`
- `comparison_history.json`

### Экспорт
- openpyxl → Excel

## Модель слоя (16 полей) — сохраняем 1:1

```
LayerIndex:
  0  NAME
  1  BINDER
  2  RAL
  3  DENSITY
  4  SOLID_CONTENT
  5  WET_THICKNESS
  6  DRY_THICKNESS
  7  THEOR_COVERING          # м²/л
  8  LOSSES                  # %
  9  PRACT_COVERING          # м²/л
 10  PRICE_KG
 11  PRICE_LITER
 12  THEOR_CONSUMPTION_KG    # кг/м²
 13  PRACT_CONSUMPTION_KG    # кг/м²
 14  COST                    # руб/м²
 15  THINNER_PERCENT
```

## Формулы (зафиксированы, менять нельзя без тестов)

1. WFT = DFT × 100 / solids_%
2. Covering_theor (м²/л) = 1000 / WFT
3. Cons_l_theor = 1 / Covering_theor
4. K_loss = 100 / (100 − losses_%)
5. Covering_pract = Covering_theor / K_loss
6. Cons_l_pract = 1 / Covering_pract
7. Cons_kg = Cons_l × density
8. Cost = PRACT_CONSUMPTION_KG × PRICE_KG

Разбавитель:
- thinner_l = parent_l × (thinner_% / 100)
- thinner_kg = thinner_l × thinner_density

## Текущая схема SQLite (упрощённая)

```sql
coatings (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  binder TEXT,
  ral TEXT,
  density REAL,
  solid_content REAL,
  price_kg REAL,
  price_liter REAL,
  is_thinner INTEGER
)

coating_templates (...)
template_layers (...)
+ history tables
```

## Критические проблемы

1. Монолит 6500+ строк
2. Слой = list по индексам (хрупко)
3. Импорты несуществующих модулей (`layer_types`, `utils`)
4. История в JSON
5. Бедная схема materials (нет C-категорий, DFT min/max, производителя и т.д.)
6. Нет систем АКЗ как полноценной сущности
7. Нет рекомендаций / scoring
8. Нет PDF
9. Нет unit-тестов
10. Нет разделения domain / infrastructure / ui

## Что обязательно сохранить

- Все формулы расчёта 1:1
- Поддержку разбавителей
- Возможность ручного редактирования параметров
- Шаблоны
- Сравнение систем
- Экспорт Excel
- Историю расчётов
- Базу материалов + CRUD
