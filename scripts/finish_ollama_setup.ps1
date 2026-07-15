param([int]$DownloadProcessId = 23368)

$ErrorActionPreference = 'Stop'
$installer = Join-Path $env:TEMP 'OllamaSetup.exe'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\Ollama'
$modelDir = Join-Path $env:LOCALAPPDATA 'OllamaModels'
$log = Join-Path $PSScriptRoot 'ollama_setup.log'

function Log([string]$Message) {
    "$(Get-Date -Format s) $Message" | Add-Content -LiteralPath $log
}

try {
    Log "Waiting for resumable installer download (PID $DownloadProcessId)."
    Wait-Process -Id $DownloadProcessId -ErrorAction SilentlyContinue
    $length = (Get-Item -LiteralPath $installer).Length
    if ($length -ne 1426239088) { throw "Installer is incomplete: $length of 1426239088 bytes." }
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid') { throw "Installer signature is not valid: $($signature.Status)." }
    Log "Download complete and Authenticode signature valid. Installing outside OneDrive."
    Start-Process -FilePath $installer -ArgumentList '/VERYSILENT','/NORESTART',("/DIR=`"$installDir`"") -Wait -WindowStyle Hidden
    $ollama = Join-Path $installDir 'ollama.exe'
    if (-not (Test-Path -LiteralPath $ollama)) { throw "Ollama executable was not installed at $ollama." }
    New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
    [Environment]::SetEnvironmentVariable('OLLAMA_MODELS', $modelDir, 'User')
    $env:OLLAMA_MODELS = $modelDir
    Log "Pulling qwen3:4b into $modelDir."
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    Start-Sleep -Seconds 5
    & $ollama pull qwen3:4b *>> $log
    $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 20
    if ($tags.models.name -notcontains 'qwen3:4b') { throw 'qwen3:4b was not returned by the Ollama API.' }
    $body = @{model='qwen3:4b'; prompt='Reply with exactly: OLLAMA READY'; stream=$false} | ConvertTo-Json
    $reply = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:11434/api/generate' -ContentType 'application/json' -Body $body -TimeoutSec 180
    Log "SUCCESS: Ollama API and qwen3:4b generation verified. Reply: $($reply.response)"
} catch {
    Log "FAILED: $($_.Exception.Message)"
    exit 1
}
