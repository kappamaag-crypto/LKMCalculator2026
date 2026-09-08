# Статус v2.0 — почти всё в GitHub

## В репозитории ✅

| Модуль | Файлы |
|--------|--------|
| Domain | enums, formulas, models, calculator, comparison, **validation** |
| Recommendation | rules, scorer, recommender |
| Services | calculation, recommendation, history |
| UI | main_window, styles, layer_table, comparison, recommendation, **history**, **materials** |
| Infra | engine, seed, logging |
| Tests | formulas, calculator, recommendations, history, excel, pdf |
| Docs + main + requirements | ✅ |

## Ещё только в ZIP (5 файлов)
- `database/models.py` (~12 KB)
- `database/repositories.py` (~12 KB)
- `excel_exporter.py` (~15 KB)
- `pdf_exporter.py` (~15 KB)
- `calculation_view.py` (~14 KB)

## ZIP
`/home/workdir/artifacts/lkm_calculator_v2.zip`

```bash
unzip lkm_calculator_v2.zip
cp -r lkm_calculator/app/infrastructure/database/models.py LKMCalculator2026/v2/app/infrastructure/database/
cp -r lkm_calculator/app/infrastructure/database/repositories.py LKMCalculator2026/v2/app/infrastructure/database/
cp -r lkm_calculator/app/infrastructure/export/*.py LKMCalculator2026/v2/app/infrastructure/export/
cp -r lkm_calculator/app/ui/views/calculation_view.py LKMCalculator2026/v2/app/ui/views/
git add v2 && git commit -m "v2.0 remaining 5 files" && git push
```
