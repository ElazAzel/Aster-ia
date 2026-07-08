# Asterion AI — локальный запуск (бэкенд + фронтенд)

# Проверка: для сборки Rust нужен GNU toolchain + GCC
$hasGcc = Get-Command gcc.exe -ErrorAction SilentlyContinue
if (-not $hasGcc) {
    Write-Host "ВНИМАНИЕ: gcc.exe не найден. Сборка Rust может не работать." -ForegroundColor Yellow
    Write-Host "Запустите scripts\bootstrap.ps1 для настройки без прав администратора." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Запуск Asterion AI..." -ForegroundColor Cyan

$backendJob = Start-Job -ScriptBlock {
    Set-Location -LiteralPath "$using:PSScriptRoot\backend"
    uv run python -m asterion_api
}

Write-Host "✔ Бэкенд запущен (фоновый процесс)" -ForegroundColor Green
Write-Host "  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host ""

try {
    Push-Location -LiteralPath "$PSScriptRoot\frontend"
    npm run dev
} finally {
    Pop-Location
    Stop-Job $backendJob
    Remove-Job $backendJob
    Write-Host "`nAsterion AI остановлен." -ForegroundColor Cyan
}
