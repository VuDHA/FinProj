<#
.SYNOPSIS
  Build the Wealth VN backend into a Tauri sidecar binary.

.DESCRIPTION
  1. Activates the Python virtual environment (if present).
  2. Runs PyInstaller using pyinstaller.spec.
  3. Renames the output to wealth-backend-x86_64-pc-windows-msvc.exe.
  4. Copies it into src-tauri/binaries/ so `cargo tauri build` can bundle it.

.NOTES
  Windows-only. Run from the backend directory:
    powershell -ExecutionPolicy Bypass -File scripts\build_sidecar.ps1
#>

[CmdletBinding()]
param(
    [string]$VenvDir = "",
    [string]$SpecFile = "",
    [string]$DistDir = "",
    [string]$BinariesDir = ""
)

# Resolve paths relative to this script.
$ScriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $VenvDir)     { $VenvDir     = Join-Path (Join-Path $ScriptRoot "..") "venv" }
if (-not $SpecFile)    { $SpecFile    = Join-Path (Join-Path $ScriptRoot "..") "pyinstaller.spec" }
if (-not $DistDir)     { $DistDir     = Join-Path (Join-Path $ScriptRoot "..") "dist" }
if (-not $BinariesDir) { $BinariesDir = Join-Path (Join-Path (Join-Path $ScriptRoot "..") "..") "src-tauri\binaries" }

$ErrorActionPreference = "Stop"

$TargetTriple = "x86_64-pc-windows-msvc"
$ExeName = "wealth-backend.exe"
$SidecarName = "wealth-backend-$TargetTriple.exe"

Write-Host "=== Wealth VN sidecar build ===" -ForegroundColor Cyan

# --- 1. Activate venv if it exists -----------------------------------------
if (Test-Path (Join-Path $VenvDir "Scripts\Activate.ps1")) {
    Write-Host "Activating virtual environment: $VenvDir" -ForegroundColor Yellow
    & (Join-Path $VenvDir "Scripts\Activate.ps1")
} else {
    Write-Host "No venv found at $VenvDir - using system Python." -ForegroundColor Yellow
}

# Ensure PyInstaller is available.
$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    python -m pip install --upgrade pyinstaller
}

# --- 2. Run PyInstaller ----------------------------------------------------
# PyInstaller must run from the backend directory so collect_submodules/collect_data_files
# can find the api/, services/, jobs/ packages.
$BackendDir = Split-Path -Parent $SpecFile
Push-Location $BackendDir
Write-Host "Running PyInstaller from $BackendDir..." -ForegroundColor Yellow
python -m PyInstaller $SpecFile --noconfirm
$pyExit = $LASTEXITCODE
Pop-Location
if ($pyExit -ne 0) {
    throw "PyInstaller build failed (exit code $pyExit)."
}
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed (exit code $LASTEXITCODE)."
}

# --- 3. Rename to target-triple filename -----------------------------------
$builtExe = Join-Path $DistDir $ExeName
if (-not (Test-Path $builtExe)) {
    throw "Expected output not found: $builtExe"
}

Write-Host "Renaming to $SidecarName..." -ForegroundColor Yellow
$sidecarPath = Join-Path $DistDir $SidecarName
Copy-Item -Path $builtExe -Destination $sidecarPath -Force

# --- 4. Copy into src-tauri/binaries/ --------------------------------------
if (-not (Test-Path $BinariesDir)) {
    New-Item -ItemType Directory -Path $BinariesDir | Out-Null
}

Write-Host "Copying sidecar to $BinariesDir..." -ForegroundColor Yellow
Copy-Item -Path $sidecarPath -Destination (Join-Path $BinariesDir $SidecarName) -Force

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Sidecar: $(Join-Path $BinariesDir $SidecarName)"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. cd src-tauri"
Write-Host "  2. cargo tauri build        # produces the installer in src-tauri/target/release/bundle"
Write-Host ""
Write-Host "For development with a live backend:" -ForegroundColor Cyan
Write-Host "  cargo tauri dev             # uses the devUrl (http://localhost:5173)"
