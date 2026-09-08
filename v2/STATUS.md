# Статус пуша v2.0

## В GitHub (v2/) — рабочее ядро

| Модуль | Статус |
|--------|--------|
| domain: enums, formulas, models, calculator, comparison, recommender | ✅ |
| services: calculation, recommendation, history | ✅ |
| ui: main_window, styles, layer_table, comparison_view | ✅ |
| infra: engine, logging | ✅ |
| main.py, requirements, docs | ✅ |

## Только в ZIP (крупные файлы)

- validation.py, rules.py, scorer.py
- database models / repositories / seed
- excel_exporter, pdf_exporter
- calculation_view, recommendation_view, history_view, materials_view
- полные tests

## Как получить всё

```bash
# Из артефактов сессии:
unzip lkm_calculator_v2.zip
cp -r lkm_calculator/* /path/to/LKMCalculator2026/v2/
cd /path/to/LKMCalculator2026
git add v2
git commit -m "v2.0 complete from zip"
git push
```

Или скачайте: `/home/workdir/artifacts/lkm_calculator_v2.zip`
