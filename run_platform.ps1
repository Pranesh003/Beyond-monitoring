Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Starting Agentic Kube AI Platform  " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Verify Prerequisites
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    exit
}
if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js (npm) is not installed or not in PATH." -ForegroundColor Red
    exit
}

# 1. Start Backend
Write-Host "`n[1/2] Initializing Python FastAPI Backend..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\backend"
if (-not (Test-Path "venv")) {
    Write-Host "Creating Virtual Environment..." -ForegroundColor Gray
    python -m venv venv
}
& ".\venv\Scripts\Activate.ps1"
Write-Host "Installing Python requirements..." -ForegroundColor Gray
pip install -r requirements.txt -q
Write-Host "Starting Uvicorn Server on port 8000..." -ForegroundColor Green
Start-Process -FilePath "uvicorn" -ArgumentList "main:app", "--reload", "--port", "8000" -WindowStyle Normal

# 2. Start Frontend
Write-Host "`n[2/2] Initializing React Vite Frontend..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\frontend"
Write-Host "Installing NPM dependencies..." -ForegroundColor Gray
npm install --legacy-peer-deps --silent
Write-Host "Starting Vite Dev Server..." -ForegroundColor Green
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WindowStyle Normal

Set-Location -Path "$PSScriptRoot"

Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host "Platform Successfully Launched in Background!" -ForegroundColor Green
Write-Host "Backend API is running at: http://127.0.0.1:8000"
Write-Host "Frontend UI is running at: http://localhost:5173"
Write-Host "=============================================" -ForegroundColor Cyan
