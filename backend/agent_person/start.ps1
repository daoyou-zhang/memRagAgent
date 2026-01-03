# AI Agent Person 启动脚本（Windows PowerShell）

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          AI Agent Person 启动中...                       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 切换到 backend 目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Split-Path -Parent $scriptPath
Set-Location $backendPath

# 加载环境变量
$envPath = Join-Path $scriptPath ".env"
if (Test-Path $envPath) {
    Write-Host "✅ 加载环境变量: $envPath" -ForegroundColor Green
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
} else {
    Write-Host "⚠️  未找到 .env 文件: $envPath" -ForegroundColor Yellow
}

# 获取端口
$port = if ($env:AGENT_PERSON_PORT) { $env:AGENT_PERSON_PORT } else { 8001 }

Write-Host ""
Write-Host "🚀 服务地址: http://localhost:$port" -ForegroundColor Green
Write-Host "📚 API 文档: http://localhost:$port/docs" -ForegroundColor Green
Write-Host "🔌 WebSocket: ws://localhost:$port/api/v1/chat/ws" -ForegroundColor Green
Write-Host "💚 健康检查: http://localhost:$port/health" -ForegroundColor Green
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动服务
python -m uvicorn agent_person.app:app --host 0.0.0.0 --port $port --reload
