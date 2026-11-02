[CmdletBinding()]
param(
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'Programs\Nexus'),
    [string]$ArchivePath
)
$ErrorActionPreference = 'Stop'
$version = 'v0.40.13'
$checksum = '7afa38624fa62ee5d8293422d0ab084c1bb4603134c7f4dafce11a033b57cc19'
$aiDirectory = Join-Path $InstallDirectory 'ai'
$exe = Join-Path $aiDirectory 'ollama.exe'
if (-not (Test-Path -LiteralPath $exe)) {
    if (-not $ArchivePath) {
        $stage = Join-Path ([IO.Path]::GetTempPath()) ('nexus-ai-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $stage -Force | Out-Null
        $ArchivePath = Join-Path $stage 'ollama-windows-amd64.zip'
        Write-Host 'Baixando Ollama oficial (aproximadamente 1,6 GB)...'
        Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/ollama/ollama/releases/download/$version/ollama-windows-amd64.zip" -OutFile $ArchivePath
    }
    if ((Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $checksum) { throw 'Pacote Ollama nao corresponde ao SHA256 verificado.' }
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $aiDirectory -Force
}
$previousHost = $env:OLLAMA_HOST
$previousModels = $env:OLLAMA_MODELS
$previousCloud = $env:OLLAMA_NO_CLOUD
try {
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    $env:OLLAMA_MODELS = Join-Path $InstallDirectory 'models\ollama'
    $env:OLLAMA_NO_CLOUD = '1'
    try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 } catch {
        Start-Process -FilePath $exe -ArgumentList 'serve' -WorkingDirectory $aiDirectory -WindowStyle Hidden
    }
    Write-Host 'Preparando modelo Qwen para conversa local (aproximadamente 1,9 GB)...'
    & $exe pull qwen2.5:3b-instruct
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao baixar o modelo de conversa.' }
    Write-Host 'Conversa pronta. Abra Nexus e escolha Conversar com Nexus no menu.'
} finally {
    $env:OLLAMA_HOST = $previousHost
    $env:OLLAMA_MODELS = $previousModels
    $env:OLLAMA_NO_CLOUD = $previousCloud
}
