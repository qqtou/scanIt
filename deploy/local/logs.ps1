# ScanIt 日志查看脚本 (Windows PowerShell)
# 用法: .\logs.ps1 [-Service backend] [-Follow] [-Tail 100]

param(
    [string]$Service = "",
    [switch]$Follow,
    [int]$Tail = 100
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
Set-Location $ProjectRoot

$Args = @("-f", "docker-compose.dev.yml", "logs")
if ($Tail -gt 0) {
    $Args += "--tail=$Tail"
}
if ($Follow) {
    $Args += "-f"
}
if ($Service) {
    $Args += $Service
}

& docker-compose @Args
