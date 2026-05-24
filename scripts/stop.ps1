$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $Root ".runtime"
$PidFile = Join-Path $RuntimeDir "aigrader_v2.pid"
$UrlPrefix = "127.0.0.1:8000"

$stopped = $false

if (Test-Path $PidFile) {
    $pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    $serverPid = 0
    if ([int]::TryParse($pidText, [ref] $serverPid)) {
        $process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $serverPid -Force
            $stopped = $true
        }
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

if (-not $stopped) {
    $netstat = netstat -ano | Select-String ":8000"
    foreach ($line in $netstat) {
        $parts = ($line.ToString() -split "\s+") | Where-Object { $_ }
        if ($parts.Count -ge 5 -and $parts[1] -like "*$UrlPrefix*") {
            $serverPid = [int]$parts[-1]
            Stop-Process -Id $serverPid -Force -ErrorAction SilentlyContinue
            $stopped = $true
        }
    }
}

if ($stopped) {
    Write-Host "实验智评 V2 已关闭。"
} else {
    Write-Host "没有发现正在运行的实验智评 V2 服务。"
}
