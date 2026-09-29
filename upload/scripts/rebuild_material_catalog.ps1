$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Root "upload\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$Builder = Join-Path $Root "upload\scripts\build_material_catalog.py"
$OutputJson = Join-Path $Root "upload\data\material_catalog_master_v3.json"
$OutputCsv = Join-Path $Root "upload\data\material_catalog_master_v3.csv"
$ReviewCsv = Join-Path $Root "upload\data\material_catalog_review_candidates_v3.csv"

$Books = @(
    "Системы 1.xls",
    "Системы 2.XLSX",
    "Системы 3.xlsx",
    "Системы 4.xlsx",
    "Таблица на 1 кв.м ЛКМ основная.xlsx"
)

Write-Host "=== LKM Calculator: expanded material master rebuild ===" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Python: $Python"
Write-Host ""

foreach ($Book in $Books) {
    $Path = Join-Path $Root ("books\" + $Book)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Не найден исходный Excel: $Path"
    }
    $Size = (Get-Item -LiteralPath $Path).Length
    Write-Host ("OK  {0}  {1:N0} bytes" -f $Book, $Size)
}

Write-Host ""
Write-Host "Запускаю расширенный генератор..." -ForegroundColor Yellow
& $Python $Builder
if ($LASTEXITCODE -ne 0) {
    throw "Генератор завершился с кодом $LASTEXITCODE"
}

Write-Host ""
Write-Host "=== GENERATED FILES ===" -ForegroundColor Green
foreach ($Path in @($OutputJson, $OutputCsv, $ReviewCsv)) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Генератор не создал файл: $Path"
    }
    $Info = Get-Item -LiteralPath $Path
    Write-Host ("{0}  {1:N0} bytes" -f $Info.FullName, $Info.Length)
}

Write-Host ""
Write-Host "Готово. Следующий запуск main.py увидит изменившийся JSON и импортирует новые записи." -ForegroundColor Green
