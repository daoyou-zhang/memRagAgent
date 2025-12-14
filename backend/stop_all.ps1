# Windows PowerShell 停止脚本
# 停止所有后端服务

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  停止所有后端服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 停止 Python 进程
Write-Host "`n正在停止服务..." -ForegroundColor Yellow

# 按端口停止
$Ports = @(5000, 5001, 8000)
foreach ($Port in $Ports) {
    $Process = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
               Select-Object -ExpandProperty OwningProcess -Unique
    if ($Process) {
        Write-Host "停止端口 $Port 的进程 (PID: $Process)..." -ForegroundColor Gray
        Stop-Process -Id $Process -Force -ErrorAction SilentlyContinue
    }
}

# 按进程名停止
Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    if ($cmdLine -match "memory|knowledge|daoyou_agent|uvicorn") {
        Write-Host "停止进程: $($_.Id) - $cmdLine" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`n所有服务已停止" -ForegroundColor Green
