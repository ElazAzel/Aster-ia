# bootstrap.ps1 - Asterion AI zero-admin setup
# Everything installs to %USERPROFILE%\.asterion\tools\

param(
    [switch]$SkipRust,
    [switch]$SkipNode,
    [switch]$SkipPython
)

$ErrorActionPreference = "Stop"
$TOOLS = "$env:USERPROFILE\.asterion\tools"
$CARGO_CONF = "$env:USERPROFILE\.cargo\config.toml"
$LLVM_URL = "https://github.com/mstorsjo/llvm-mingw/releases/download/20250114/llvm-mingw-20250114-ucrt-x86_64.zip"
$LLVM_DIR = "$TOOLS\llvm-mingw"
$LLVM_ZIP = "$TOOLS\llvm-mingw.zip"

Write-Host "=== Asterion AI Bootstrap (no admin) ===" -ForegroundColor Cyan
Write-Host "Tools dir: $TOOLS`n" -ForegroundColor DarkGray

function Ensure-Dir($p) {
    if (-not (Test-Path -LiteralPath $p)) {
        New-Item -ItemType Directory -Path $p -Force | Out-Null
        Write-Host "  + Created: $p" -ForegroundColor Green
    }
}

# ===== 1. Rust =====

if (-not $SkipRust) {
    Write-Host "`n[1/3] Rust..." -ForegroundColor Yellow

    $hasRustup = (Get-Command rustup -ErrorAction SilentlyContinue) -ne $null
    if (-not $hasRustup) {
        Write-Host "  -> Downloading rustup-init.exe ..." -ForegroundColor Gray
        $ru = "$env:TEMP\rustup-init.exe"
        Invoke-WebRequest -Uri "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe" -OutFile $ru
        Start-Process -FilePath $ru -ArgumentList "-y --default-toolchain stable --profile default" -Wait -NoNewWindow
        Remove-Item $ru -Force
        $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
        Write-Host "  + rustup installed" -ForegroundColor Green
    } else {
        Write-Host "  + rustup already present" -ForegroundColor Green
    }

    # GNU toolchain
    $gnuList = rustup toolchain list 2>&1 | Out-String
    if ($gnuList -notlike "*stable-x86_64-pc-windows-gnu*") {
        rustup toolchain install stable-x86_64-pc-windows-gnu
        Write-Host "  + GNU toolchain installed" -ForegroundColor Green
    }
    rustup default stable-x86_64-pc-windows-gnu | Out-Null
    Write-Host "  + default: stable-x86_64-pc-windows-gnu" -ForegroundColor Green

    # LLVM MinGW portable
    if (-not (Test-Path -LiteralPath "$LLVM_DIR\bin\gcc.exe")) {
        Write-Host "  -> Downloading LLVM MinGW portable ..." -ForegroundColor Gray
        Ensure-Dir $TOOLS
        Invoke-WebRequest -Uri $LLVM_URL -OutFile $LLVM_ZIP
        Write-Host "  -> Extracting ..." -ForegroundColor Gray
        Expand-Archive -Path $LLVM_ZIP -DestinationPath $TOOLS -Force
        Remove-Item $LLVM_ZIP -Force
        Write-Host "  + LLVM MinGW extracted to $LLVM_DIR" -ForegroundColor Green
    } else {
        Write-Host "  + LLVM MinGW already present" -ForegroundColor Green
    }

    # Add to current session PATH
    $env:Path = "$LLVM_DIR\bin;$env:Path"

    # Create dummy libgcc_eh.a for LLVM MinGW
    $LIB_DIR = "$LLVM_DIR\lib\gcc\x86_64-w64-mingw32"
    if (-not (Test-Path -LiteralPath "$LIB_DIR\libgcc_eh.a")) {
        $arExe = "$LLVM_DIR\bin\llvm-ar.exe"
        if (Test-Path -LiteralPath $arExe) {
            Ensure-Dir $LIB_DIR
            & $arExe rc "$LIB_DIR\libgcc_eh.a" 2>$null
            Write-Host "  + Dummy libgcc_eh.a created" -ForegroundColor Green
        }
    }

    # Configure Cargo to use our GCC
    Ensure-Dir "$env:USERPROFILE\.cargo"
    $escapedPath = $LLVM_DIR -replace '\\', '/'
    $linkerLine = "[target.x86_64-pc-windows-gnu]`nlinker = `"$escapedPath/bin/gcc.exe`""
    if (-not (Test-Path -LiteralPath $CARGO_CONF)) {
        $linkerLine | Set-Content -Path $CARGO_CONF
        Write-Host "  + Cargo config created" -ForegroundColor Green
    } elseif ((Get-Content $CARGO_CONF -Raw) -notlike "*llvm-mingw*") {
        "$linkerLine`n$(Get-Content $CARGO_CONF -Raw)" | Set-Content -Path $CARGO_CONF
        Write-Host "  + Cargo config updated" -ForegroundColor Green
    }
}

# ===== 2. Node.js (via fnm) =====

if (-not $SkipNode) {
    Write-Host "`n[2/3] Node.js..." -ForegroundColor Yellow
    $hasNode = (Get-Command node -ErrorAction SilentlyContinue) -ne $null
    if (-not $hasNode) {
        $hasFnm = (Get-Command fnm -ErrorAction SilentlyContinue) -ne $null
        if (-not $hasFnm) {
            Write-Host "  -> Installing fnm (Node.js manager, per-user) ..." -ForegroundColor Gray
            $zip = "$env:TEMP\fnm.zip"
            Invoke-WebRequest -Uri "https://github.com/Schniz/fnm/releases/latest/download/fnm-windows.zip" -OutFile $zip
            Ensure-Dir "$TOOLS\fnm"
            Expand-Archive -Path $zip -DestinationPath "$TOOLS\fnm" -Force
            Remove-Item $zip -Force
            $env:Path = "$TOOLS\fnm;$env:Path"
            Write-Host "  + fnm installed" -ForegroundColor Green
        }
        fnm env --use-on-cd | Out-String | Invoke-Expression
        fnm install 22
        fnm default 22
        Write-Host "  + Node.js 22 installed via fnm" -ForegroundColor Green
    } else {
        Write-Host "  + Node.js already present ($(node --version))" -ForegroundColor Green
    }
}

# ===== 3. Python (via uv) =====

if (-not $SkipPython) {
    Write-Host "`n[3/3] Python..." -ForegroundColor Yellow
    $hasUv = (Get-Command uv -ErrorAction SilentlyContinue) -ne $null
    if (-not $hasUv) {
        Write-Host "  -> Installing uv (per-user) ..." -ForegroundColor Gray
        $env:UV_UNMANAGED_INSTALL = "1"
        $script = "$env:TEMP\install-uv.ps1"
        Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $script
        & $script
        Remove-Item $script -Force
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
        Write-Host "  + uv installed" -ForegroundColor Green
    } else {
        Write-Host "  + uv already present" -ForegroundColor Green
    }

    # Python via uv (no admin)
    $pyVer = uv run python --version 2>$null
    if (-not $pyVer) {
        uv python install 3.12
        Write-Host "  + Python 3.12 installed" -ForegroundColor Green
    } else {
        Write-Host "  + Python already present" -ForegroundColor Green
    }

    # Sync deps
    $venvPath = Join-Path -LiteralPath $PSScriptRoot "..\backend\.venv"
    if (-not (Test-Path -LiteralPath $venvPath)) {
        Push-Location -LiteralPath "$PSScriptRoot\..\backend"
        uv sync
        Pop-Location
        Write-Host "  + Python deps installed" -ForegroundColor Green
    } else {
        Write-Host "  + .venv already exists" -ForegroundColor Green
    }
}

# ===== Finish =====

Write-Host "`n=== Done! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Run project:" -ForegroundColor White
Write-Host "  .\dev.ps1"
Write-Host ""
Write-Host "Verify Rust:" -ForegroundColor White
Write-Host "  cargo test -p asterion-core"
Write-Host ""
Write-Host "Verify Python:" -ForegroundColor White
Write-Host "  cd backend; uv run pytest"
Write-Host ""
Write-Host "If gcc still not found, restart terminal or run:" -ForegroundColor DarkGray
Write-Host "  `$env:Path = `"$LLVM_DIR\bin;`$env:Path`"" -ForegroundColor DarkGray
