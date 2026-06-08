#!/bin/bash
# Linux / macOS installer for ComfyUI

InstallDir="$HOME/.asterion/comfyui"
echo -e "\033[0;36m=============================================\033[0m"
echo -e "\033[0;36mAsterion AI: Установка локального ComfyUI\033[0m"
echo -e "\033[0;36mПапка установки: $InstallDir\033[0m"
echo -e "\033[0;36m=============================================\033[0m"

# 1. Clone repository if not exists
if [ ! -d "$InstallDir" ]; then
    echo -e "\033[0;33m[1/4] Клонирование репозитория ComfyUI...\033[0m"
    git clone https://github.com/comfyanonymous/ComfyUI.git "$InstallDir"
else
    echo -e "\033[0;32m[1/4] Репозиторий ComfyUI уже клонирован.\033[0m"
fi

# 2. Setup python virtual environment
cd "$InstallDir" || exit
if [ ! -d "venv" ]; then
    echo -e "\033[0;33m[2/4] Создание Python виртуального окружения (venv)...\033[0m"
    python3 -m venv venv
else
    echo -e "\033[0;32m[2/4] Виртуальное окружение venv уже существует.\033[0m"
fi

# 3. Install requirements
echo -e "\033[0;33m[3/4] Установка зависимостей (PyTorch и др.)...\033[0m"
./venv/bin/pip install --upgrade pip

# Check for CUDA or MPS
CudaAvailable=false
if command -v nvidia-smi &> /dev/null; then
    CudaAvailable=true
fi

if [ "$CudaAvailable" = true ]; then
    echo -e "\033[0;32mОбнаружена NVIDIA GPU. Устанавливаем PyTorch с CUDA...\033[0m"
    ./venv/bin/pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "\033[0;32mОбнаружена macOS. Устанавливаем PyTorch с поддержкой Metal (MPS)...\033[0m"
    ./venv/bin/pip install torch torchvision torchaudio
else
    echo -e "\033[0;30mNVIDIA GPU не найдена. Устанавливаем CPU-версию PyTorch...\033[0m"
    ./venv/bin/pip install torch torchvision torchaudio
fi

./venv/bin/pip install -r requirements.txt

# 4. Download lightweight Model checkpoint (SD 1.5 Pruned SafeTensors)
ModelPath="models/checkpoints/v1-5-pruned-emaonly.safetensors"
if [ ! -f "$ModelPath" ]; then
    echo -e "\033[0;33m[4/4] Загрузка базовой модели SD 1.5 (v1-5-pruned-emaonly.safetensors)...\033[0m"
    ModelUrl="https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
    curl -L -o "$ModelPath" "$ModelUrl"
    echo -e "\033[0;32mМодель успешно загружена.\033[0m"
else
    echo -e "\033[0;32m[4/4] Базовая модель SD 1.5 уже загружена.\033[0m"
fi

echo -e "\033[0;32m=============================================\033[0m"
echo -e "\033[0;32mЛокальный ComfyUI успешно настроен!\033[0m"
echo -e "\033[0;32mДля запуска выполните: ./venv/bin/python main.py\033[0m"
echo -e "\033[0;32m=============================================\033[0m"
