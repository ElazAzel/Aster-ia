# Asterion AI — локальный запуск (бэкенд + фронтенд)

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
