# Windows PowerShell Setup Script for SLM Enterprise AI Platform Backend
# This script ensures a clean python local environment setup on Windows without compiler requirements.

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting SLM Enterprise AI Platform Compiler-Free Windows Setup..." -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Detect Python
$pythonBin = "python"
try {
    $pythonVersionStr = & $pythonBin -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
} catch {
    Write-Host "❌ Python could not be found. Please install Python 3.10+ and make sure it is added to your PATH environment variable." -ForegroundColor Red
    Exit 1
}

Write-Host "✓ Detected Python version: $pythonVersionStr" -ForegroundColor Green

# Validate Python version >= 3.10
$versionParts = $pythonVersionStr.Split('.')
$major = [int]$versionParts[0]
$minor = [int]$versionParts[1]

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
    Write-Host "❌ Python 3.10+ is required. Found Python $pythonVersionStr." -ForegroundColor Red
    Exit 1
}

# 2. Clean up existing virtual environments to avoid state conflicts
if (Test-Path "venv") {
    Write-Host "🧹 Removing old virtual environment (venv) to prevent dependency conflicts..." -ForegroundColor Yellow
    Remove-Item -Path "venv" -Recurse -Force
}

# 3. Create clean virtual environment
Write-Host "📦 Creating a fresh virtual environment..." -ForegroundColor Cyan
& $pythonBin -m venv venv

# 4. Activate virtual environment and upgrade packaging tools
Write-Host "🔌 Activating virtual environment & upgrading pip, setuptools, and wheel..." -ForegroundColor Cyan
$envPath = Join-Path (Get-Location) "venv"
$pipBin = Join-Path $envPath "Scripts\pip.exe"
$pythonVenvBin = Join-Path $envPath "Scripts\python.exe"

& $pythonVenvBin -m pip install --upgrade pip setuptools wheel

# 5. Install dependencies using binary-only flag to prevent local C++ compilation requirement
Write-Host "📦 Installing core dependencies using binary wheels only..." -ForegroundColor Cyan
Write-Host "   (This prevents pip from attempting to compile packages like pydantic-core from source)" -ForegroundColor Gray

# We use --only-binary :all: to force pip to fetch precompiled wheels.
# -e . installs the current package in editable mode.
& $pipBin install --only-binary :all: -e .

# 6. Create the environment configuration file if it does not exist
if (-not (Test-Path ".env")) {
    Write-Host "⚙️ Creating .env configuration file from Windows template..." -ForegroundColor Yellow
    Copy-Item -Path ".env.windows.example" -Destination ".env"
}

# 7. Ask to download local SLM GGUF Model weights
Write-Host "=================================================================" -ForegroundColor Cyan
$title = "Local SLM GGUF Model Setup"
$message = "Do you want to download Microsoft's Phi-3-Mini GGUF model (approx. 2.2 GB)?"
$yes = New-Object System.Management.Automation.Host.ChoiceDescription "&Yes", "Downloads the 2.2GB Microsoft Phi-3-Mini model to enable full offline AI orchestration."
$no = New-Object System.Management.Automation.Host.ChoiceDescription "&No", "Skips model download. The platform will degrade gracefully to local SRE deterministic fallback rules."
$options = [System.Management.Automation.Host.ChoiceDescription[]]($yes, $no)
$result = $host.ui.PromptForChoice($title, $message, $options, 1) # Default is No

if ($result -eq 0) {
    Write-Host "🧠 Launching Automated SLM GGUF Downloader..." -ForegroundColor Cyan
    & $pythonVenvBin ..\scripts\download_model.py
} else {
    Write-Host "💡 Skipped GGUF model download. Platform will use deterministic SRE engine fallbacks." -ForegroundColor Yellow
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "✅ Compiler-free setup completed successfully on Windows!" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next steps to start testing locally on Windows:"
Write-Host ""
Write-Host "1. Activate your virtual environment in PowerShell:"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "2. Run the FastAPI backend server:"
Write-Host "   uvicorn app.main:app --reload --host 127.0.0.1 --port 8001"
Write-Host ""
Write-Host "3. Verify local server runtime:"
Write-Host "   Invoke-RestMethod -Uri http://127.0.0.1:8001/api/v1/health"
Write-Host ""
