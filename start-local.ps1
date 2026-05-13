# ScanIt 本地启动脚本 (无 Docker 版)
# 用法: .\start-local.ps1 [-Init]

param(
    [switch]$Init
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "=== ScanIt 本地启动 ===" -ForegroundColor Cyan

# 1. 检查 Python
Write-Host "[INFO] 检查 Python..." -ForegroundColor Yellow
$pythonVer = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python 未安装" -ForegroundColor Red
    exit 1
}
Write-Host "  $pythonVer" -ForegroundColor Gray

# 2. 检查 Node.js
Write-Host "[INFO] 检查 Node.js..." -ForegroundColor Yellow
$nodeVer = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Node.js 未安装" -ForegroundColor Red
    exit 1
}
Write-Host "  $nodeVer" -ForegroundColor Gray

# 3. 检查 .env 文件
if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Write-Host "[INFO] 复制环境变量模板..." -ForegroundColor Yellow
    Copy-Item (Join-Path $ProjectRoot "deploy\local\.env.example") (Join-Path $ProjectRoot ".env")
    Write-Host "[WARN] 请编辑 .env 填写 API Key！" -ForegroundColor Red
}

# 4. 创建 Python 虚拟环境
if (-not (Test-Path (Join-Path $BackendDir "venv"))) {
    Write-Host "[INFO] 创建 Python 虚拟环境..." -ForegroundColor Yellow
    python -m venv (Join-Path $BackendDir "venv")
    Write-Host "[OK] 虚拟环境创建完成" -ForegroundColor Green
}

# 5. 激活虚拟环境并安装依赖
Write-Host "[INFO] 检查 Python 依赖..." -ForegroundColor Yellow
$ActivateScript = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
. $ActivateScript

# 安装核心依赖（跳过重型包加速安装）
$CoreDeps = @(
    "fastapi", "uvicorn[standard]", "pydantic", "pydantic-settings",
    "sqlalchemy", "aiosqlite", "alembic",
    "celery", "redis",
    "python-multipart", "python-jose[cryptography]", "passlib[bcrypt]",
    "httpx", "python-dotenv", "aiofiles",
    "slowapi", "requests", "beautifulsoup4"
)
foreach ($dep in $CoreDeps) {
    pip install $dep --quiet 2>$null
}
Write-Host "[OK] Python 依赖就绪" -ForegroundColor Green

# 6. 初始化数据库
$DbFile = Join-Path $BackendDir "scanit_dev.db"
if ($Init -or -not (Test-Path $DbFile)) {
    Write-Host "[INFO] 初始化 SQLite 数据库..." -ForegroundColor Yellow
    Push-Location $BackendDir
    python scripts/init_sqlite.py
    Pop-Location
}

# 7. 安装前端依赖
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "[INFO] 安装前端依赖..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
    Write-Host "[OK] 前端依赖安装完成" -ForegroundColor Green
}

# 8. 启动后端
Write-Host ""
Write-Host "=== 启动后端 API ===" -ForegroundColor Cyan
Push-Location $BackendDir
Start-Process powershell -ArgumentList "-NoExit", "-Command", ". $ActivateScript; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Pop-Location

# 9. 启动前端
Write-Host "=== 启动前端 ===" -ForegroundColor Cyan
Push-Location $FrontendDir
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev"
Pop-Location

Write-Host ""
Write-Host "=== 启动完成 ===" -ForegroundColor Green
Write-Host "后端 API: http://localhost:8000" -ForegroundColor Green
Write-Host "API 文档: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "前端:     http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "[INFO] 默认管理员: admin / admin123" -ForegroundColor Yellow
Write-Host "[WARN] 请登录后修改密码！" -ForegroundColor Red
Write-Host ""
Write-Host "按任意键退出（关闭所有窗口）..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
