$ErrorActionPreference = "Stop"

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw "The packaged gateway helper currently targets Windows only."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

python --version
if ($LASTEXITCODE -ne 0) { throw "Python is required to build the JARVIS gateway sidecar." }

python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }

python -m pip install -e ".\services\gateway" pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Failed to install gateway packaging dependencies." }

$env:PYTHONPATH = Join-Path $repoRoot "services\gateway"
python -m PyInstaller --clean --noconfirm --onefile --name jarvis-gateway --collect-all fastapi --collect-all starlette --collect-all uvicorn "services\gateway\entrypoint.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed to package the gateway." }

$rustInfo = rustc -vV
if ($LASTEXITCODE -ne 0) { throw "Rust stable toolchain is required to identify the sidecar target." }

$hostLine = $rustInfo | Where-Object { $_ -like "host:*" } | Select-Object -First 1
if (-not $hostLine) { throw "Could not determine the Rust target triple." }
$targetTriple = ($hostLine -split ":", 2)[1].Trim()

$binaryDirectory = Join-Path $repoRoot "apps\desktop\src-tauri\binaries"
New-Item -ItemType Directory -Force $binaryDirectory | Out-Null
$targetPath = Join-Path $binaryDirectory "jarvis-gateway-$targetTriple.exe"
Copy-Item (Join-Path $repoRoot "dist\jarvis-gateway.exe") $targetPath -Force

Write-Host "JARVIS gateway sidecar created: $targetPath"
