# Windows PowerShell installer for ComfyUI

$InstallDir = "$Home\.asterion\comfyui"
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Asterion AI: Установка локального ComfyUI" -ForegroundColor Cyan
Write-Host "Папка установки: $InstallDir" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Clone repository if not exists
if (-not (Test-Path $InstallDir)) {
    Write-Host "[1/4] Клонирование репозитория ComfyUI..." -ForegroundColor Yellow
    git clone https://github.com/comfyanonymous/ComfyUI.git $InstallDir
} else {
    Write-Host "[1/4] Репозиторий ComfyUI уже клонирован." -ForegroundColor Green
}

# 2. Setup python virtual environment
cd $InstallDir
if (-not (Test-Path "venv")) {
    Write-Host "[2/4] Создание Python виртуального окружения (venv)..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "[2/4] Виртуальное окружение venv уже существует." -ForegroundColor Green
}

# 3. Install requirements
Write-Host "[3/4] Установка зависимостей (PyTorch и др.)..." -ForegroundColor Yellow
& ".\venv\Scripts\pip" install --upgrade pip

# Check if CUDA is available
$CudaAvailable = $false
try {
    $nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if ($nvidiaSmi) {
        $CudaAvailable = $true
    }
} catch {}

if ($CudaAvailable) {
    Write-Host "Обнаружена NVIDIA GPU. Устанавливаем PyTorch с CUDA..." -ForegroundColor Green
    & ".\venv\Scripts\pip" install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
} else {
    Write-Host "NVIDIA GPU не найдена. Устанавливаем CPU-версию PyTorch..." -ForegroundColor Gray
    & ".\venv\Scripts\pip" install torch torchvision torchaudio
}

& ".\venv\Scripts\pip" install -r requirements.txt

# 4. Download lightweight Model checkpoint (SD 1.5 Pruned SafeTensors)
$ModelPath = "models\checkpoints\v1-5-pruned-emaonly.safetensors"
if (-not (Test-Path $ModelPath)) {
    Write-Host "[4/4] Загрузка базовой модели SD 1.5 (v1-5-pruned-emaonly.safetensors)..." -ForegroundColor Yellow
    $ModelUrl = "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
    Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelPath -UserAgent "Mozilla/5.0"
    Write-Host "Модель успешно загружена." -ForegroundColor Green
} else {
    Write-Host "[4/4] Базовая модель SD 1.5 уже загружена." -ForegroundColor Green
}

Write-Host "=============================================" -ForegroundColor Green
Write-Host "Локальный ComfyUI успешно настроен!" -ForegroundColor Green
Write-Host "Для запуска выполните: .\venv\Scripts\python main.py" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
