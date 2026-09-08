# Статус пуша v2.0

## В репозитории (main/v2)

### Domain
- enums, formulas, models, calculator, comparison
- recommendation/recommender.py + __init__.py

### Services
- calculation_service, recommendation_service, history_service

### Infrastructure
- database/engine.py
- logging, package inits

### UI
- styles, layer_table widget, package inits

### Docs
- 01–07 (summary), README, STATUS, DOWNLOAD

### Tests
- test_history.py

## Ещё в ZIP (не в git)
- validation.py, rules.py, scorer.py
- database models/repositories/seed
- excel_exporter, pdf_exporter
- main_window + all views
- remaining tests

## Полный исходник
`/home/workdir/artifacts/lkm_calculator_v2.zip`

```bash
unzip lkm_calculator_v2.zip
cp -r lkm_calculator/* LKMCalculator2026/v2/
cd LKMCalculator2026 && git add v2 && git commit -m "v2.0 full" && git push
```
