$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ReleaseRoot = Join-Path $Root "release"
$PackageName = "AIGRADER_V2_PORTABLE_$Timestamp"
$PackageDir = Join-Path $ReleaseRoot $PackageName
$ZipPath = Join-Path $ReleaseRoot ($PackageName + ".zip")

function Copy-Directory {
    param(
        [Parameter(Mandatory = $true)] [string] $Source,
        [Parameter(Mandatory = $true)] [string] $Destination
    )
    if (!(Test-Path $Source)) {
        throw "Missing directory: $Source"
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

Write-Host "=================================================="
Write-Host " AIGRADER V2 portable package builder"
Write-Host "=================================================="
Write-Host ""

$FrontendDist = Join-Path $Root "frontend\dist\index.html"
if (!(Test-Path $FrontendDist)) {
    throw "frontend\dist was not found. Run npm run build in the frontend directory first."
}

$RuntimePython = Join-Path $Root "runtime\python\python.exe"
if (!(Test-Path $RuntimePython)) {
    throw "runtime\python\python.exe was not found. Portable package requires bundled Python runtime."
}

Remove-Item -LiteralPath $PackageDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $PackageDir -Force | Out-Null

Write-Host "[1/5] Copy backend ..."
Copy-Directory -Source (Join-Path $Root "backend\app") -Destination (Join-Path $PackageDir "backend\app")
Copy-Item -LiteralPath (Join-Path $Root "backend\requirements.txt") -Destination (Join-Path $PackageDir "backend\requirements.txt") -Force

Write-Host "[2/5] Copy frontend dist ..."
Copy-Directory -Source (Join-Path $Root "frontend\dist") -Destination (Join-Path $PackageDir "frontend\dist")

Write-Host "[3/5] Copy bundled Python runtime ..."
Copy-Directory -Source (Join-Path $Root "runtime") -Destination (Join-Path $PackageDir "runtime")
if (Test-Path (Join-Path $PackageDir "runtime\libreoffice\program\soffice.exe")) {
    Write-Host "      Bundled LibreOffice converter: included" -ForegroundColor Green
} else {
    Write-Host "      Bundled LibreOffice converter: not found, Word preview may fall back to HTML on other computers." -ForegroundColor Yellow
}

Write-Host "[4/5] Copy startup scripts and docs ..."
Copy-Directory -Source (Join-Path $Root "scripts") -Destination (Join-Path $PackageDir "scripts")
$BatFiles = Get-ChildItem -LiteralPath $Root -Filter "*.bat" | Where-Object { $_.Name -notlike "*_开发版.bat" }
if (-not $BatFiles) {
    throw "Startup BAT file was not found."
}
foreach ($bat in $BatFiles) {
    Copy-Item -LiteralPath $bat.FullName -Destination (Join-Path $PackageDir $bat.Name) -Force
}
Copy-Item -LiteralPath (Join-Path $Root "README.md") -Destination (Join-Path $PackageDir "README.md") -Force

@"
AIGRADER V2 Portable Package

1. Extract the whole folder.
2. Double-click the startup BAT file.
3. Keep the command window open while using the system.
4. If the browser does not open automatically, copy the URL shown in the command window.
5. Runtime data is stored under backend\data, backend\uploads and backend\exports.
6. This package includes Python runtime. Normal users do not need Python, Node.js or npm.
7. If runtime\libreoffice\program\soffice.exe exists, Word reports can be previewed as PDF without installing Word/WPS.
"@ | Set-Content -LiteralPath (Join-Path $PackageDir "USAGE.txt") -Encoding ASCII

New-Item -ItemType Directory -Path (Join-Path $PackageDir "backend\data") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $PackageDir "backend\uploads") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $PackageDir "backend\exports") -Force | Out-Null

Write-Host "[5/5] Create zip ..."
Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath -Force

if (!(Test-Path $ZipPath)) {
    throw "Failed to create zip: $ZipPath"
}

Write-Host ""
Write-Host "Package folder: $PackageDir" -ForegroundColor Green
Write-Host "Package zip: $ZipPath" -ForegroundColor Green
