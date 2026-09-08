# Статус v2.0

## В GitHub

### Domain ✅
enums, formulas, models, calculator, comparison
recommendation: rules, scorer, recommender

### Services ✅
calculation, recommendation, history

### UI ✅
main_window, styles, layer_table
comparison_view, recommendation_view

### Infra ✅
engine, seed, logging

### Tests ✅
test_formulas, test_history, test_pdf_export

### Docs + main.py + requirements ✅

## Ещё только в ZIP (~6 файлов)
- validation.py
- database/models.py, repositories.py
- excel_exporter.py, pdf_exporter.py
- calculation_view, history_view, materials_view
- test_calculator, test_recommendations, test_excel_export

## Полный исходник
`/home/workdir/artifacts/lkm_calculator_v2.zip`

```bash
unzip lkm_calculator_v2.zip
cp -r lkm_calculator/* LKMCalculator2026/v2/
git add v2 && git commit -m "v2.0 remaining large modules" && git push
```
