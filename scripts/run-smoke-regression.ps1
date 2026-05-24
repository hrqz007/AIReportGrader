param(
    [switch]$UseSystemPython
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BundledPython = Join-Path $ProjectRoot "runtime\python\python.exe"
$TestScript = Join-Path $ProjectRoot "tests\smoke_regression.py"

Write-Host "==============================================="
Write-Host " AIReportGrader V2 smoke regression"
Write-Host "==============================================="
Write-Host "Project root: $ProjectRoot"
Write-Host ""

if ($UseSystemPython) {
    $PythonExe = "python"
} elseif (Test-Path $BundledPython) {
    $PythonExe = $BundledPython
} else {
    $PythonExe = "python"
}

Write-Host "[1/2] Compile Python files ..."
& $PythonExe -m compileall (Join-Path $ProjectRoot "backend") (Join-Path $ProjectRoot "tests") -q

Write-Host "[2/2] Run core workflow smoke regression ..."
& $PythonExe $TestScript

Write-Host ""
Write-Host "Smoke regression passed."
