# ScanIt 本机启动脚本 (Windows PowerShell)
# 用法: .\start.ps1 [-Build] [-SkipFrontend]

param(
    [switch]$Build,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
Set-Location $ProjectRoot

Write-Host "=== ScanIt 本机启动 ===" -ForegroundColor Cyan

# 1. 检查 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "[INFO] 复制环境变量模板..." -ForegroundColor Yellow
    Copy-Item "deploy\local\.env.example" ".env"
    Write-Host "[WARN] 请编辑 .env 填写 API Key！" -ForegroundColor Red
    Write-Host "       - GOOGLE_API_KEY 或 BOCHA_API_KEY（搜索）" -ForegroundColor Yellow
    Write-Host "       - OLLAMA_BASE_URL 或其他 LLM API Key" -ForegroundColor Yellow
}

# 2. 检查 Docker
Write-Host "[INFO] 检查 Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
} catch {
    Write-Host "[ERROR] Docker 未运行！请启动 Docker Desktop。" -ForegroundColor Red
    exit 1
}

# 3. 构建参数
$ComposeArgs = @("-f", "docker-compose.dev.yml", "up", "-d")
if ($Build) {
    $ComposeArgs = @("-f", "docker-compose.dev.yml", "up", "-d", "--build")
}

# 4. 启动服务
Write-Host "[INFO] 启动服务..." -ForegroundColor Yellow
& docker $ComposeArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] 启动失败！" -ForegroundColor Red
    exit 1
}

# 5. 等待数据库就绪
Write-Host "[INFO] 等待数据库就绪..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 6. 运行数据库迁移
Write-Host "[INFO] 运行数据库迁移..." -ForegroundColor Yellow
docker exec scanit-backend alembic upgrade head 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] 数据库迁移完成" -ForegroundColor Green
} else {
    Write-Host "[WARN] 数据库迁移跳过（可能已完成）" -ForegroundColor Yellow
}

# 7. 初始化默认租户
Write-Host "[INFO] 初始化默认租户..." -ForegroundColor Yellow
docker exec scanit-backend python -m scripts.migrate_default_tenant 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] 默认租户初始化完成" -ForegroundColor Green
} else {
    Write-Host "[WARN] 默认租户初始化跳过（可能已存在）" -ForegroundColor Yellow
}

# 8. 显示状态
Write-Host ""
Write-Host "=== 服务状态 ===" -ForegroundColor Cyan
docker ps --filter "name=scanit" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host ""
Write-Host "=== 访问地址 ===" -ForegroundColor Cyan
Write-Host "前端:     http://localhost:3000" -ForegroundColor Green
Write-Host "后端 API: http://localhost:8000" -ForegroundColor Green
Write-Host "API 文档: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Flower:   http://localhost:5555" -ForegroundColor Green
Write-Host ""
Write-Host "[OK] 启动完成！" -ForegroundColor Green
