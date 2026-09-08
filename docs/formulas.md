# Формулы LKMCalculator 2026 v3.0

## Версия

`FORMULA_VERSION = 3.0`

Промежуточные значения не округляются. Округление выполняется только при отображении или на границе закупочной фасовки.

## 1. DFT → WFT

При известной объёмной доле сухого остатка `SV`:

```text
WFT = DFT / (SV / 100)
```

Единицы:

- DFT — мкм;
- WFT — мкм;
- SV — % по объёму.

Пример: `100 мкм / 70% = 142.857 мкм`.

## 2. Разбавление

База разбавления должна храниться явно.

### BY_PAINT_VOLUME

```text
V_thinner = V_paint × p
V_mix = V_paint × (1 + p)
```

где `p = dilution_percent / 100`.

### BY_MIX_VOLUME

Если процент относится к конечному объёму смеси:

```text
V_mix = V_paint / (1 - p)
V_thinner = V_mix - V_paint
```

### BY_MASS

```text
m_thinner = m_paint × p
V_thinner = m_thinner / rho_thinner
```

### BY_COMPONENT_VOLUME

Используется только при явном указании, относительно какого компонента задана дозировка.

## 3. Теоретический расход исходного ЛКМ

```text
V_theoretical = DFT / (10 × SV_fraction)
```

где `SV_fraction = SV / 100`.

Эквивалентная форма:

```text
V_theoretical = 1000 / WFT
```

Результат — л/м².

Для `DFT=100 мкм`, `SV=70%`:

```text
WFT = 142.857 мкм
V_theoretical = 0.142857 л/м²
```

Важно: это 142.857 мл/м², а не 14.286 мл/м².

## 4. Потери

```text
K_loss = 1 / (1 - loss_fraction)
V_practical = V_theoretical × K_loss
```

Например, при потерях 10%:

```text
K_loss = 1 / 0.90 = 1.111111...
```

## 5. Плотность

```text
m = V × rho
```

где `rho` — кг/л.

## 6. Стоимость

```text
Cost = mass × price_per_kg
```

Денежные расчёты в коммерческом слое должны использовать `Decimal`.

## 7. Фасовка

```text
packages = ceil(required / package_size)
purchase = packages × package_size
remainder = purchase - required
```

Технологические потери и закупочный резерв — разные величины.

## 8. 2К

При массовом соотношении `A:B`:

```text
A = M_mix × A_ratio / (A_ratio + B_ratio)
B = M_mix × B_ratio / (A_ratio + B_ratio)
```

Для объёмного соотношения сначала определяется объём смеси с учётом плотностей компонентов.

## 9. Точка росы

```text
margin = T_surface - T_dew_point
```

Условие допуска:

```text
margin >= required_margin
```

При невыполнении в технологическом контроле формируется блокирующая ошибка.

## 10. Версионирование

Любой сохранённый расчёт должен содержать:

- `formula_version`;
- `calculator_version`;
- дату расчёта;
- snapshot исходных данных.
