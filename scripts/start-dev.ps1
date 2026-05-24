$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$BackendVenv = Join-Path $Backend ".venv"
$PythonExe = Join-Path $BackendVenv "Scripts\python.exe"
$PipExe = Join-Path $BackendVenv "Scripts\pip.exe"

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

function Find-Npm {
    $cmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidateDirs = @(
        "C:\Program Files\nodejs",
        "C:\Program Files (x86)\nodejs",
        "C:\Program Files\Microsoft Visual Studio\18\Insiders\MSBuild\Microsoft\VisualStudio\NodeJs",
        "D:\软件\HBuilder\HBuilderX\plugins\npm"
    )
    foreach ($dir in $candidateDirs) {
        $npm = Join-Path $dir "npm.cmd"
        if (Test-Path $npm) {
            $env:Path = "$dir;$env:Path"
            return $npm
        }
    }
    return $null
}

Write-Host "=================================================="
Write-Host " 实验智评 V2 开发启动器"
Write-Host "=================================================="
Write-Host ""
Write-Host "项目目录：$Root"

if (!(Test-Path $PythonExe)) {
    Write-Host "[1/4] 正在创建后端 Python 虚拟环境 ..."
    $BasePython = Find-BasePython
    if (-not $BasePython) {
        Write-Host "[错误] 没有找到 Python。请先安装 Python 3.11 或更高版本。" -ForegroundColor Red
        exit 1
    }
    if ($BasePython.Length -gt 1) {
        & $BasePython[0] $BasePython[1] -m venv $BackendVenv
    } else {
        & $BasePython[0] -m venv $BackendVenv
    }
}

Write-Host "[2/4] 正在安装或检查后端依赖 ..."
try {
    & $PipExe install -r (Join-Path $Backend "requirements.txt")
} catch {
    Write-Host "默认源安装失败，正在尝试使用清华镜像源 ..." -ForegroundColor Yellow
    & $PipExe install -r (Join-Path $Backend "requirements.txt") -i https://pypi.tuna.tsinghua.edu.cn/simple
}

Write-Host "[3/4] 正在启动后端 API 服务 ..."
$BackendArgs = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--reload"
)
Start-Process -FilePath $PythonExe -ArgumentList $BackendArgs -WorkingDirectory $Backend

Write-Host "[4/4] 正在启动前端开发服务 ..."
$NpmExe = Find-Npm
if (-not $NpmExe) {
    Write-Host ""
    Write-Host "[错误] 没有找到 npm，前端页面无法启动。" -ForegroundColor Red
    Write-Host "请安装完整 Node.js LTS 版本，或将 npm.cmd 所在目录加入系统 PATH。"
    Write-Host "安装地址：https://nodejs.org/"
    Write-Host "后端已经启动；前端暂未启动。"
    exit 1
}
if (!(Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "首次启动需要安装前端依赖 ..."
    Push-Location $Frontend
    & $NpmExe install
    Pop-Location
}
Start-Process -FilePath $NpmExe -ArgumentList @("run", "dev") -WorkingDirectory $Frontend

Start-Sleep -Seconds 4
Start-Process "http://127.0.0.1:5173"

Write-Host ""
Write-Host "后端 API： http://127.0.0.1:8000/api/health"
Write-Host "前端页面： http://127.0.0.1:5173"
Write-Host ""
Write-Host "注意：这是 V2 开发版启动脚本，两个服务会分别在后台窗口运行。"
