# NeuroWeave Portable Setup Script (PowerShell Version)
# Run: powershell -ExecutionPolicy Bypass -File setup_portable.ps1

param(
    [switch]$SkipDeps = $false
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Type = "INFO")
    $colors = @{
        "INFO"  = "Cyan"
        "OK"    = "Green"
        "WARN"  = "Yellow"
        "ERROR" = "Red"
    }
    Write-Host "[$Type] $Message" -ForegroundColor $colors[$Type]
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

Write-Header "NeuroWeave Portable Installation"

# Check Python
try {
    $pythonVersion = python --version 2>&1 | Select-String "Python (\d+\.\d+)" | ForEach-Object { $_.Matches.Groups[1].Value }
    Write-Status "Python $pythonVersion found" "OK"
} catch {
    Write-Status "Python 3.9+ not found in PATH" "ERROR"
    Write-Host ""
    Write-Host "Please install Python from https://www.python.org" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    exit 1
}

# Create virtual environment
$venvPath = Join-Path (Get-Location) "backend" ".venv"
if (Test-Path $venvPath) {
    Write-Status "Virtual environment already exists at backend\.venv" "WARN"
} else {
    Write-Status "Creating virtual environment..."
    cd backend
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Failed to create virtual environment" "ERROR"
        exit 1
    }
    Write-Status "Virtual environment created" "OK"
    cd ..
}

# Activate venv
Write-Status "Activating virtual environment..."
$activateScript = Join-Path $venvPath "Scripts" "Activate.ps1"
& $activateScript

# Install dependencies
Write-Host ""
Write-Status "Installing dependencies (this may take 5-15 minutes)..."
cd backend
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Status "Failed to install dependencies" "ERROR"
    exit 1
}
Write-Status "Dependencies installed" "OK"

# Initialize database
Write-Host ""
Write-Status "Checking database..."
if (-not (Test-Path "data.db")) {
    Write-Status "Creating SQLite database..."
    python -c "import sqlite3; sqlite3.connect('data.db').executescript(open('sql/schema.sql').read())"
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Database initialized" "OK"
    } else {
        Write-Status "Database initialization completed (may create on first run)" "WARN"
    }
} else {
    Write-Status "Database already exists" "OK"
}

cd ..

Write-Header "Setup Complete!"

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run: .\run_all.bat" -ForegroundColor White
Write-Host "     (or run .\run_backend.bat and .\run_desktop.bat separately)" -ForegroundColor Gray
Write-Host "  2. Backend will be available at http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  3. Desktop app will connect automatically" -ForegroundColor White
Write-Host ""
