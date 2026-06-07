# Скрипт автоматической установки Rust (cargo/rustc) и компилятора MSVC C++ Build Tools

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Установка окружения компиляции для Asterion AI" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Проверка и установка MSVC Build Tools
Write-Host "`n[1/2] Скачивание Visual Studio Build Tools..." -ForegroundColor Yellow
$vsPath = "$env:TEMP\vs_buildtools.exe"
Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vs_buildtools.exe" -OutFile $vsPath

Write-Host "Запуск установки MSVC C++ Build Tools..." -ForegroundColor Yellow
Write-Host "Внимание: Будет запрошено подтверждение прав администратора (UAC)." -ForegroundColor Yellow
Write-Host "Пожалуйста, дождитесь завершения установки в открывшемся окне." -ForegroundColor Yellow

# Запуск установщика с рабочей нагрузкой компилятора C++
Start-Process -FilePath $vsPath -ArgumentList "--passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended" -Verb RunAs -Wait

Write-Host "Установка MSVC C++ Build Tools завершена." -ForegroundColor Green

# 2. Проверка и установка Rust
Write-Host "`n[2/2] Скачивание установщика Rust (Rustup)..." -ForegroundColor Yellow
$rustupPath = "$env:TEMP\rustup-init.exe"
Invoke-WebRequest -Uri "https://win.rustup.rs/x86_64" -OutFile $rustupPath

Write-Host "Запуск установки Rust..." -ForegroundColor Yellow
# Запускаем rustup-init в тихом режиме
Start-Process -FilePath $rustupPath -ArgumentList "-y --default-host x86_64-pc-windows-msvc" -Wait

Write-Host "Установка Rust завершена." -ForegroundColor Green
Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Все компоненты успешно установлены!" -ForegroundColor Green
Write-Host " Пожалуйста, ПЕРЕЗАПУСТИТЕ терминал/IDE, чтобы обновить переменные окружения PATH." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
