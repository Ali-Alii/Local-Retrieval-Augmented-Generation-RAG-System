param(
    [switch]$SkipInstall,
    [switch]$SkipIndex
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found. Install it and retry."
    }
}

"docker", "uv", "dotnet", "npm", "ollama", "pwsh" | ForEach-Object { Assert-Command $_ }

if (-not $SkipInstall) {
    uv sync --python 3.12
    Push-Location frontend
    try { npm ci } finally { Pop-Location }
}

docker compose up -d mongodb weaviate

if (-not $SkipIndex) {
    $weaviateReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Invoke-RestMethod "http://127.0.0.1:8080/v1/.well-known/ready" -TimeoutSec 2 | Out-Null
            $weaviateReady = $true
            break
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $weaviateReady) { throw "Weaviate did not become ready within 60 seconds." }
    $schema = Invoke-RestMethod "http://127.0.0.1:8080/v1/schema" -TimeoutSec 5
    $collectionExists = $schema.classes | Where-Object { $_.class -eq "CISControlsV8" }
    if (-not $collectionExists) {
        Write-Host "Initializing the exact 332-chunk Weaviate index..." -ForegroundColor Cyan
        uv run python -m rag.exact_pipeline weaviate
    } else {
        Write-Host "Weaviate index already exists; keeping the persisted collection." -ForegroundColor Green
    }
}

$python = @'
$env:RAG_RUNTIME="exact"
uv run python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
'@
$middleware = @'
$env:Jwt__SigningKey="local-development-key-change-before-production-2026"
$env:Mongo__ConnectionString="mongodb://127.0.0.1:27017"
$env:Authentication__EnableDevelopmentLogin="true"
dotnet run --project middleware/src/RagMiddleware.Api --urls http://127.0.0.1:5100
'@
$frontend = @'
Set-Location frontend
npm run dev -- --host 127.0.0.1
'@

Start-Process pwsh -ArgumentList "-NoExit", "-Command", $python -WorkingDirectory $root
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $middleware -WorkingDirectory $root
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $frontend -WorkingDirectory $root

Write-Host "Sentinel services are starting." -ForegroundColor Green
Write-Host "Open http://127.0.0.1:5173 after all three terminals report ready."
Write-Host "Use Local demo login. Exact-runtime startup can take about two minutes."
