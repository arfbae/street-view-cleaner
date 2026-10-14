Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 STARTING STREET-VIEW & INSTAGRAM CLEANER DEPLOYMENT" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Environment Verification
if (-not (Test-Path ".env")) {
    Write-Host "⚠️ Warning: .env file not found. Creating from .env.example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ .env created. Please fill in your live API keys if using providers." -ForegroundColor Green
    } else {
        Write-Error "❌ Error: Neither .env nor .env.example exists. Deployment aborted."
        Exit
    }
}

# 2. Local Python Dependency Pre-check (Optional Loop Detection)
if (Test-Path "verify_imports.py") {
    Write-Host "⏳ Running pre-deployment import loop sanity check..." -ForegroundColor Cyan
    python verify_imports.py
    if (\$LASTEXITCODE -ne 0) {
        Write-Error "❌ Error: Project contains circular imports or module syntax issues. Fixed required before container build."
        Exit
    }
}

# 3. Docker Orchestration Build
Write-Host "⏳ Building application image components and starting stack..." -ForegroundColor Cyan
docker-compose up --build -d

# 4. Active Health State Verification
Write-Host "⏳ Waiting for API engine to report healthy status..." -ForegroundColor Cyan
\$retries = 10
\(healthy =\)false

while (\(retries -gt 0 -and -not\)healthy) {
    \(status = docker inspect --format='{{.State.Health.Status}}' street-view-cleaner-backend 2>\)null
    if (\$status -eq "healthy") {
        \(healthy =\)true
    } else {
        Write-Host "⏳ App starting (Current state: \(status)... Retries left:\)retries"
        Start-Sleep -Seconds 3
        \$retries--
    }
}

if (\$healthy) {
    Write-Host "`n==========================================================" -ForegroundColor Green
    Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host "➔ Frontend Application Interface open on: http://localhost" -ForegroundColor Green
    Write-Host "➔ API Gateway Engine open on: http://localhost:8000" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Host "`n❌ ERROR: System containers are running, but the API failed healthchecks." -ForegroundColor Red
    Write-Host "Run 'docker-compose logs backend' to debug engine initialization faults." -ForegroundColor Red
}
