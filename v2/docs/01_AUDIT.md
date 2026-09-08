# Этап 1. Аудит существующего проекта LKMCalculator2026

## Структура репозитория
- Calv1Grah1.py — главный GUI (монолит)
- coatings.db — SQLite база материалов и систем
- Excel-шаблоны, документация

## Формулы (зафиксированы 1:1)
- WFT = DFT × 100 / solids_%
- Covering = 1000 / WFT
- K_loss = 100 / (100 − losses_%)
- Practical covering = theor / K_loss
- Consumption L = 1 / covering
- Consumption kg = consumption_L × density
- Cost = consumption_kg × price_per_kg

## Проблемы старой версии
- Монолитный GUI
- Слабая валидация
- Нет recommendation / comparison engine
- Смешение UI и бизнес-логики

Полный аудит — в архиве проекта.
