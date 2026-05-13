# ScanIt 停止脚本 (Windows PowerShell)
# 用法: .\stop.ps1 [-Clean]

param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
Set-Location $ProjectRoot

Write-Host "=== 停止 ScanIt 服务 ===" -ForegroundColor Cyan

if ($Clean) {
    Write-Host "[INFO] 停止并清理容器、网络、卷..." -ForegroundColor Yellow
    docker-compose -f docker-compose.dev.yml down -v --remove-orphans
    Write-Host "[OK] 清理完成" -ForegroundColor Green
} else {
    Write-Host "[INFO] 停止容器..." -ForegroundColor Yellow
    docker-compose -f docker-compose.dev.yml down
    Write-Host "[OK] 已停止" -ForegroundColor Green
}
