[CmdletBinding()]
param(
    [switch]$NoInstall,
    [switch]$SkipCollect
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uploadDir = (Resolve-Path $scriptDir).Path
$repoDir = Split-Path -Parent $uploadDir
Set-Location $uploadDir

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python не найден в PATH. Установите Python 3.11+ и повторите запуск."
}

Write-Host "=== LKMCalculator2026 :: полный regression run ===" -ForegroundColor Cyan
Write-Host "Repo:   $repoDir"
Write-Host "Upload: $uploadDir"
Write-Host ""

if (-not $NoInstall) {
    $requirements = Join-Path $uploadDir "requirements.txt"
    if (Test-Path $requirements) {
        Write-Host "[1/4] Проверка зависимостей..." -ForegroundColor Yellow
        & $python.Source -m pip install -r $requirements
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    else {
        Write-Host "[1/4] requirements.txt не найден — пропускаю установку." -ForegroundColor DarkYellow
    }
}
else {
    Write-Host "[1/4] Установка зависимостей отключена (-NoInstall)." -ForegroundColor DarkYellow
}

$env:PYTHONPATH = "."
$resultsDir = Join-Path $uploadDir ".test-results"
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
$junit = Join-Path $resultsDir "pytest-junit.xml"
$collectFile = Join-Path $resultsDir "pytest-collect.txt"

Write-Host ""
Write-Host "[2/4] Полный pytest..." -ForegroundColor Yellow
& $python.Source -m pytest -q --junitxml=$junit
$pytestExit = $LASTEXITCODE

$collected = @()
if (-not $SkipCollect) {
    Write-Host ""
    Write-Host "[3/4] Сбор списка тестов для привязки к §1–§32..." -ForegroundColor Yellow
    & $python.Source -m pytest --collect-only -q *> $collectFile
    $collectExit = $LASTEXITCODE
    if ($collectExit -ne 0) {
        Write-Warning "pytest --collect-only завершился с кодом $collectExit; привязка тестов будет UNKNOWN."
    }
    elseif (Test-Path $collectFile) {
        $collected = Get-Content $collectFile | Where-Object { $_ -match "::test_" }
    }
}

$sectionTests = [ordered]@{
    "1" = @("test_calculator", "test_formulas", "test_calculation")
    "2" = @("calculation_view_smoke", "view_smoke", "ui_smoke")
    "3" = @("adhoc", "ad_hoc")
    "4" = @("comparison", "multilayer")
    "5" = @("excel", "customer_excel")
    "6" = @("pdf")
    "7" = @("formulas", "precision", "units")
    "8" = @("2k", "two_component", "multilayer")
    "9" = @("packaging", "packaging_planner")
    "10" = @("backup", "restore", "alembic", "database")
    "11" = @("sha", "seal", "verify", "material_restore")
    "11.1" = @("notification_outbox", "outbox")
    "12" = @("engineering_context", "history", "tds")
    "13" = @("surface", "preparation", "profile", "condition")
    "14" = @("tds", "spkeffa", "normative")
    "15" = @()
    "16" = @("recommendation", "score")
    "17" = @("inspection_view", "inspection", "dft")
    "18" = @("acceptance", "release")
    "19" = @("parity", "legacy")
    "20" = @("system", "systems", "knowledge", "kb")
    "21" = @("compatibility")
    "22" = @("lkm_prof", "lkmprof", "prof")
    "23" = @("pre_application", "preapplication")
    "24" = @("chemical", "resistance")
    "25" = @("catalog", "tds", "normative")
    "26" = @("explanation", "loss", "provenance")
    "27" = @("staging", "matching", "provenance")
    "28" = @("loss_profile", "lossprofile", "loss")
    "29" = @("confirm_draft", "draft")
    "30" = @("decision_log", "decision")
    "31" = @("scenario")
    "32" = @("inspection", "dft", "multilayer")
}

$manualSections = @{
    "2" = "UI/offscreen smoke"
    "5" = "Excel visual/print acceptance"
    "6" = "PDF visual/print acceptance"
    "14" = "SPKEFFA TDS E2E"
    "15" = "ОТЛОЖЕНО"
    "18" = "release acceptance evidence"
    "20" = "UI/E2E"
    "22" = "LKM-Prof acceptance"
    "23" = "pre-application E2E"
    "24" = "source-backed matrix acceptance"
    "25" = "full catalog E2E"
    "29" = "service/UI acceptance"
    "31" = "scenario UI"
    "32" = "inspection runtime/E2E"
}

function Get-SectionEvidence([string]$section) {
    $patterns = $sectionTests[$section]
    if ($null -eq $patterns -or $patterns.Count -eq 0) { return @() }
    $hits = @()
    foreach ($nodeid in $collected) {
        foreach ($pattern in $patterns) {
            if ($nodeid -like "*$pattern*") {
                $hits += $nodeid
                break
            }
        }
    }
    return $hits | Sort-Object -Unique
}

function Get-JunitSectionStatus([string]$section) {
    if (-not (Test-Path $junit)) { return "UNKNOWN" }
    $evidence = @(Get-SectionEvidence $section)
    if ($evidence.Count -eq 0) { return "NO_DIRECT_TEST" }

    try {
        [xml]$xml = Get-Content $junit
        $cases = @($xml.testsuites.testsuite.testcase)
        $matched = @()
        foreach ($case in $cases) {
            foreach ($nodeid in $evidence) {
                if ($nodeid -like "*::$($case.name)") {
                    $matched += $case
                    break
                }
            }
        }
        if ($matched.Count -eq 0) { return "UNKNOWN" }
        if ($matched | Where-Object { $_.failure -or $_.error -or $_.skipped }) { return "FAIL_OR_SKIPPED" }
        return "PASS"
    }
    catch {
        return "UNKNOWN"
    }
}

Write-Host ""
Write-Host "[4/4] Сводка по §1–§32" -ForegroundColor Yellow
Write-Host "PASS = связанные тесты прошли; FAIL_OR_SKIPPED = есть failure/error/skip; NO_DIRECT_TEST = прямого теста не найдено; UNKNOWN = доказательство нельзя определить автоматически; MANUAL = нужна ручная/E2E проверка."
Write-Host ""

$planPath = Join-Path $repoDir "docs\plan2akz.md"
$planText = if (Test-Path $planPath) { Get-Content $planPath -Raw } else { "" }

$planStatus = @{}
foreach ($line in ($planText -split "`r?`n")) {
    if ($line -match '^\|\s*(11\.1|\d+)\s*\|\s*([^|]+)\|') {
        $planStatus[$matches[1]] = $matches[2].Trim()
    }
}

foreach ($section in $sectionTests.Keys) {
    $p = if ($planStatus.ContainsKey($section)) { $planStatus[$section] } else { "UNKNOWN" }
    $t = Get-JunitSectionStatus $section
    $evidence = @(Get-SectionEvidence $section)
    $manual = if ($manualSections.ContainsKey($section)) { $manualSections[$section] } else { "" }

    $detail = "tests=$($evidence.Count)"
    if ($manual) { $detail += "; manual=$manual" }
    Write-Host ("§{0,-4} plan={1,-18} tests={2,-16} {3}" -f $section, $p, $t, $detail)
}

Write-Host ""
Write-Host "Pytest exit code: $pytestExit" -ForegroundColor $(if ($pytestExit -eq 0) { "Green" } else { "Red" })
Write-Host "JUnit: $junit"
if (-not $SkipCollect) { Write-Host "Collection: $collectFile" }
Write-Host ""
Write-Host "ВАЖНО: PASS тестов не переводит пункт plan2akz.md в ВЫПОЛНЕНО автоматически. Для закрытия требуется код + проверочное доказательство + отдельная фиксация в плане."
Write-Host ""

if ($pytestExit -ne 0) { exit $pytestExit }
exit 0
