$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$FrontendDist = Join-Path $Root "frontend\dist\index.html"
$RuntimePython = Join-Path $Root "runtime\python\python.exe"
$RuntimePip = Join-Path $Root "runtime\python\Scripts\pip.exe"
$BackendVenv = Join-Path $Backend ".venv"
$VenvPython = Join-Path $BackendVenv "Scripts\python.exe"
$VenvPip = Join-Path $BackendVenv "Scripts\pip.exe"
$RuntimeDir = Join-Path $Root ".runtime"
$LogDir = Join-Path $Root ".streamlit_runtime"
$PidFile = Join-Path $RuntimeDir "aigrader_v2.pid"
$OutLog = Join-Path $LogDir "v2_stdout.log"
$ErrLog = Join-Path $LogDir "v2_stderr.log"
$Url = "http://127.0.0.1:8000"
$PythonExe = $null
$PipExe = $null

function Ensure-Dir {
    param([Parameter(Mandatory = $true)] [string] $Path)
    if (!(Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Find-BasePython {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @($py.Source, "-3")
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }
    return $null
}

function Test-BackendDependencies {
    param([Parameter(Mandatory = $true)] [string] $Python)

    $code = "import importlib.util, sys; mods=['fastapi','uvicorn','pandas','openpyxl','docx','openai','PIL','multipart']; missing=[m for m in mods if importlib.util.find_spec(m) is None]; sys.exit(1 if missing else 0)"
    $null = & $Python -c $code 2>$null
    return $LASTEXITCODE -eq 0
}

function Install-BackendDependencies {
    param([Parameter(Mandatory = $true)] [string] $Pip)

    $requirements = Join-Path $Backend "requirements.txt"
    try {
        & $Pip install -r $requirements --no-warn-script-location
    } catch {
        & $Pip install -r $requirements -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location
    }
}

function Test-Health {
    try {
        Invoke-WebRequest -UseBasicParsing "$Url/api/health" -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

Ensure-Dir $RuntimeDir
Ensure-Dir $LogDir

if (!(Test-Path $FrontendDist)) {
    throw "Frontend dist file not found: $FrontendDist"
}

if (Test-Path $RuntimePython) {
    $PythonExe = $RuntimePython
    $PipExe = $RuntimePip
    $env:PYTHONUTF8 = "1"
    $env:PYTHONNOUSERSITE = "1"
    $env:PATH = (Join-Path $Root "runtime\python") + ";" + (Join-Path $Root "runtime\python\Scripts") + ";" + $env:PATH
} else {
    if (!(Test-Path $VenvPython)) {
        $BasePython = Find-BasePython
        if (-not $BasePython) {
            throw "Python was not found. Install Python 3.11+ or use the bundled runtime package."
        }
        if ($BasePython.Length -gt 1) {
            & $BasePython[0] $BasePython[1] -m venv $BackendVenv
        } else {
            & $BasePython[0] -m venv $BackendVenv
        }
    }
    $PythonExe = $VenvPython
    $PipExe = $VenvPip
}

if (!(Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}
if (!(Test-Path $PipExe)) {
    throw "pip executable not found: $PipExe"
}

if (!(Test-BackendDependencies -Python $PythonExe)) {
    Install-BackendDependencies -Pip $PipExe
}
if (!(Test-BackendDependencies -Python $PythonExe)) {
    throw "Backend dependencies are incomplete. Check network access or requirements.txt."
}

if (Test-Health) {
    Start-Process $Url
    exit 0
}

$args = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")
$process = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList $args `
    -WorkingDirectory $Backend `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -PassThru

$process.Id | Set-Content -Path $PidFile -Encoding ASCII

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Health) {
        $ready = $true
        break
    }
}

if ($ready) {
    Start-Process $Url
} else {
    Start-Process "notepad.exe" $ErrLog
}
