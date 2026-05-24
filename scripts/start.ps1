$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$FrontendDist = Join-Path $Root "frontend\dist\index.html"
$RuntimePython = Join-Path $Root "runtime\python\python.exe"
$RuntimePip = Join-Path $Root "runtime\python\Scripts\pip.exe"
$BackendVenv = Join-Path $Backend ".venv"
$VenvPython = Join-Path $BackendVenv "Scripts\python.exe"
$VenvPip = Join-Path $BackendVenv "Scripts\pip.exe"
$PythonExe = $null
$PipExe = $null
$Url = "http://127.0.0.1:8000"
$RunServer = Join-Path $Root "scripts\run_server.py"

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

    $code = "import importlib.util, sys; mods=['fastapi','uvicorn','pandas','openpyxl','docx','openai','PIL','multipart']; missing=[m for m in mods if importlib.util.find_spec(m) is None]; print('missing=' + ','.join(missing)); sys.exit(1 if missing else 0)"
    $null = & $Python -c $code 2>$null
    return $LASTEXITCODE -eq 0
}

function Install-BackendDependencies {
    param([Parameter(Mandatory = $true)] [string] $Pip)

    $requirements = Join-Path $Backend "requirements.txt"
    try {
        & $Pip install -r $requirements --no-warn-script-location
    } catch {
        Write-Host "默认源安装失败，正在尝试使用清华镜像源 ..." -ForegroundColor Yellow
        & $Pip install -r $requirements -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location
    }
}

Write-Host "=================================================="
Write-Host " 实验智评 V2 启动器"
Write-Host "=================================================="
Write-Host ""
Write-Host "项目目录：$Root"
Write-Host ""

if (!(Test-Path $FrontendDist)) {
    Write-Host "[错误] 没有找到前端构建文件：$FrontendDist" -ForegroundColor Red
    Write-Host "请先在开发机器上执行：frontend 目录下 npm install 和 npm run build。"
    Write-Host "如果这是发给老师使用的压缩包，请确认压缩包中包含 frontend\dist 目录。"
    exit 1
}

if (Test-Path $RuntimePython) {
    Write-Host "[1/3] 检测到内置便携运行环境。"
    $PythonExe = $RuntimePython
    $PipExe = $RuntimePip
    $env:PYTHONUTF8 = "1"
    $env:PYTHONNOUSERSITE = "1"
    $env:PATH = (Join-Path $Root "runtime\python") + ";" + (Join-Path $Root "runtime\python\Scripts") + ";" + $env:PATH
} else {
    Write-Host "[1/3] 未检测到内置运行环境，准备使用本机 Python。"
    if (!(Test-Path $VenvPython)) {
        Write-Host "正在创建后端 Python 虚拟环境 ..."
        $BasePython = Find-BasePython
        if (-not $BasePython) {
            Write-Host "[错误] 没有找到 Python。请先安装 Python 3.11 或更高版本，或使用包含 runtime 的便携版。" -ForegroundColor Red
            exit 1
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
    Write-Host "[错误] Python 运行程序不存在：$PythonExe" -ForegroundColor Red
    exit 1
}

if (!(Test-Path $PipExe)) {
    Write-Host "[错误] pip 不存在：$PipExe" -ForegroundColor Red
    exit 1
}

Write-Host "[2/3] 正在检查后端依赖 ..."
if (!(Test-BackendDependencies -Python $PythonExe)) {
    Write-Host "依赖不完整，正在安装后端依赖 ..."
    Install-BackendDependencies -Pip $PipExe
}

if (!(Test-BackendDependencies -Python $PythonExe)) {
    Write-Host "[错误] 后端依赖仍未安装完整，请检查网络或 requirements.txt。" -ForegroundColor Red
    exit 1
}

Write-Host "运行环境检查通过。"

Write-Host "[3/3] 正在启动实验智评 ..."
Write-Host "系统网址：$Url"
Write-Host "请不要关闭当前命令行窗口；关闭后系统会停止运行。"
Write-Host "如果浏览器没有自动打开，请手动复制上面的系统网址访问。"
Write-Host ""

& $PythonExe $RunServer
