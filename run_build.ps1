# Скрипт сборки установщика Asterion AI с обновлением переменных окружения PATH

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Запуск процесса сборки установщика Asterion AI" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Обновляем PATH текущего процесса из реестра
Write-Host "`nОбновление переменных окружения PATH..." -ForegroundColor Yellow
$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

# Добавляем стандартные пути cargo и Visual Studio Build Tools на всякий случай
$cargoPath = "$env:USERPROFILE\.cargo\bin"
if (Test-Path $cargoPath) {
    $env:Path = "$cargoPath;$env:Path"
}

# 2. Проверяем доступность cargo и rustc
Write-Host "`nПроверка инструментов Rust..." -ForegroundColor Yellow
cargo --version
rustc --version

# 3. Сборка фронтенда
Write-Host "`nСборка фронтенда..." -ForegroundColor Yellow
npm --prefix frontend run build

# 4. Сборка установщика Tauri (с ограничением параллельных потоков во избежание блокировок антивирусом)
Write-Host "`nСборка десктопного установщика через Tauri CLI..." -ForegroundColor Yellow
$env:CARGO_BUILD_JOBS = 1
npx @tauri-apps/cli build

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Сборка завершена!" -ForegroundColor Green
Write-Host " Установщик расположен в папке: src-tauri\target\release\bundle" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
