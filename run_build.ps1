# Asterion AI Desktop Installer Build Script

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Launching Asterion AI Desktop Installer Build" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Refresh PATH from Registry
Write-Host "`nRefreshing PATH environment variables..." -ForegroundColor Yellow
$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

# Add standard cargo path just in case
$cargoPath = "$env:USERPROFILE\.cargo\bin"
if (Test-Path $cargoPath) {
    $env:Path = "$cargoPath;$env:Path"
}

# 2. Check Rust compiler tools
Write-Host "`nChecking Rust Toolchain..." -ForegroundColor Yellow
cargo --version
rustc --version

# 3. Compile frontend
Write-Host "`nCompiling Svelte frontend..." -ForegroundColor Yellow
npm --prefix frontend run build

# 4. Compile Tauri installer with retry loop to handle Windows file-locking conflicts
$env:CARGO_BUILD_JOBS = 1
$retryCount = 0
$maxRetries = 5
$success = $false

while (-not $success -and $retryCount -lt $maxRetries) {
    $retryCount++
    Write-Host "`nTauri build attempt $retryCount of $maxRetries..." -ForegroundColor Yellow
    npx @tauri-apps/cli build
    
    if ($LASTEXITCODE -eq 0) {
        $success = $true
    } else {
        Write-Host "Build interrupted (possibly due to antivirus file lock). Retrying in 5 seconds..." -ForegroundColor Red
        Start-Sleep -Seconds 5
    }
}

if (-not $success) {
    Write-Error "Tauri build failed after $maxRetries attempts."
    exit 1
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Desktop Installer Build Complete!" -ForegroundColor Green
Write-Host " Output Folder: src-tauri\target\release\bundle" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
