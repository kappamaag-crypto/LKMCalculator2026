# Восстановление полных исходников

Из-за лимита размера API часть файлов при пуше была сокращена.

## Полный исходник (без сокращений)

Архив сессии разработки:

```
/home/workdir/artifacts/lkm_calculator_v2.zip
```

Или папка:

```
/home/workdir/artifacts/lkm_calculator/
```

## Как восстановить в GitHub одной командой

```bash
# на машине, где есть полный исходник и git clone репо
cd LKMCalculator2026
unzip /path/to/lkm_calculator_v2.zip
# или: cp -a /path/to/lkm_calculator/. v2/
rm -rf v2 && mv lkm_calculator v2   # если распаковали в lkm_calculator/
# правильнее:
cp -a lkm_calculator/. v2/
git add v2
git commit -m "v2.0: restore full sources without API truncation"
git push
```

## Файлы, которые были сильнее всего сокращены в API-пуше

- app/infrastructure/export/excel_exporter.py
- app/infrastructure/export/pdf_exporter.py
- app/ui/views/calculation_view.py
- app/domain/validation.py
- tests/test_calculator.py, test_recommendations.py
- docs/*

После `cp` из ZIP эти файлы станут полными.
