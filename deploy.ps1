[CmdletBinding()]
param(
    [switch]$Down,
    [switch]$Logs,
    [switch]$NoBuild,
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$ComposeService = "street-view-cleaner"

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE"
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required. Install/start Docker Desktop, then run this script again."
}

if ($Down) {
    Invoke-Compose down
    exit 0
}

if (-not (Test-Path ".env")) {
    if (-not (Test-Path ".env.template")) {
        throw "Missing .env.template; run this script from the project root."
    }
    Copy-Item ".env.template" ".env"
    Write-Warning "Created .env from .env.template. Add Qwen/Nano Banana/Google credentials before live processing."
}

$upArgs = @("up", "-d")
if (-not $NoBuild) { $upArgs += "--build" }
Invoke-Compose @upArgs

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        & docker compose exec -T $ComposeService python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()" *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Invoke-Compose ps
    Invoke-Compose logs --tail 100 $ComposeService
    throw "The application did not become healthy within $TimeoutSeconds seconds."
}

Invoke-Compose ps
Write-Host "Street View Cleaner is ready at http://localhost:8000"
Write-Host "Use .\deploy.ps1 -Logs to follow logs or .\deploy.ps1 -Down to stop the stack."

if ($Logs) {
    Invoke-Compose logs -f $ComposeService
}
