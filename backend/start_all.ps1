# Windows PowerShell 启动脚本
# 启动所有后端服务：daoyou_agent, memory, knowledge

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  memRagAgent 后端服务启动脚本 (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 激活虚拟环境
$VenvPath = "..\venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Host "`n[1/4] 激活虚拟环境..." -ForegroundColor Yellow
    & $VenvPath
} else {
    Write-Host "`n[警告] 虚拟环境不存在: $VenvPath" -ForegroundColor Red
    Write-Host "请先创建虚拟环境: python -m venv ../venv" -ForegroundColor Red
    exit 1
}

# 启动 Memory 服务 (端口 5000)
Write-Host "`n[2/4] 启动 Memory 服务 (端口 5000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir\memory'; ..\..\..\venv\Scripts\Activate.ps1; python app.py" -WindowStyle Normal

# 启动 Knowledge 服务 (端口 5001)
Write-Host "[3/4] 启动 Knowledge 服务 (端口 5001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir\knowledge'; ..\..\..\venv\Scripts\Activate.ps1; python app.py" -WindowStyle Normal

# 等待依赖服务启动
Write-Host "`n等待依赖服务启动 (3秒)..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# 启动 daoyou_agent 服务 (端口 8000) - 在当前窗口
Write-Host "[4/4] 启动 daoyou_agent 服务 (端口 8000)..." -ForegroundColor Yellow
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  所有服务已启动！" -ForegroundColor Green
Write-Host "  - Memory:      http://localhost:5000" -ForegroundColor Green
Write-Host "  - Knowledge:   http://localhost:5001" -ForegroundColor Green
Write-Host "  - Agent:       http://localhost:8000" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

python -m uvicorn daoyou_agent.app:app --host 0.0.0.0 --port 8000 --reload
