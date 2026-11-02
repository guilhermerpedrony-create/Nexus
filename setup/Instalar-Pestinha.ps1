[CmdletBinding()]
param(
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'Programs\Pestinha'),
    [string]$SourceDirectory,
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$commit = '25fd74be2aeab6935bf8a7459963374f48d5d28b'
$expectedHash = '1E420AB71AE7C798F063769364B11047F063EDB0F3208EA90BF30A90CD19A630'
if ($env:OS -ne 'Windows_NT') { throw 'Este instalador requer Windows.' }
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Esta distribuicao requer Windows de 64 bits.' }
$InstallDirectory = [IO.Path]::GetFullPath($InstallDirectory)
$exe = Join-Path $InstallDirectory 'Pestinha.exe'
$running = @(Get-Process -Name Pestinha -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe })
if ($running.Count) { throw 'Feche o Pestinha pelo menu dele antes de reinstalar. A memoria sera preservada.' }

if (-not $SourceDirectory) {
    $staging = Join-Path ([IO.Path]::GetTempPath()) ('pestinha-install-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    $archive = Join-Path $staging 'pestinha.zip'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Write-Host 'Baixando a versao verificada do repositorio original...'
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/mille-okws/pestinha/archive/$commit.zip" -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $staging
    $repo = Join-Path $staging "pestinha-$commit"
    $SourceDirectory = Join-Path (Join-Path $repo ('execut' + [char]0x00e1 + 'veis')) 'windows'
} else {
    $SourceDirectory = [IO.Path]::GetFullPath($SourceDirectory)
    $repo = Split-Path (Split-Path $SourceDirectory -Parent) -Parent
}
$sourceExe = Join-Path $SourceDirectory 'Pestinha.exe'
if ((Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'O executavel nao corresponde a versao verificada. Instalacao interrompida.'
}
foreach ($folder in @('assets', 'pets')) {
    if (-not (Test-Path -LiteralPath (Join-Path $SourceDirectory $folder) -PathType Container)) {
        throw "Pasta obrigatoria ausente: $folder"
    }
}
New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
Copy-Item -LiteralPath $sourceExe -Destination $exe -Force
foreach ($folder in @('assets', 'pets')) {
    $destination = Join-Path $InstallDirectory $folder
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Get-ChildItem -LiteralPath (Join-Path $SourceDirectory $folder) -Force | Copy-Item -Destination $destination -Recurse -Force
}
foreach ($file in @('LICENSE', 'PRIVACIDADE.md', 'README.md')) {
    $original = Join-Path $repo $file
    if (Test-Path -LiteralPath $original) { Copy-Item -LiteralPath $original -Destination $InstallDirectory -Force }
}
$memory = Join-Path $InstallDirectory 'memory'
New-Item -ItemType Directory -Path $memory -Force | Out-Null
$permissions = Join-Path $memory 'permissions.json'
if (-not (Test-Path -LiteralPath $permissions)) {
    # Perfil normal: mesmas opcoes padrao do projeto; primeira instalacao somente.
    $settings = [ordered]@{
        ativo = $true; pet = 'bryan'; travessuras = $false; memes = $true
        fotos = $false; bilhetes = $true; cutucar = $true; carinho = $true
        arrastar = $true; pousar_janelas = $true; tela_cheia = $false
        rotina = $true; modo_teste = $false; mostrar_emocao = $false
        bolinha = $true; fogos = $true
    }
    [IO.File]::WriteAllText($permissions, ($settings | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
}
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$programs = [Environment]::GetFolderPath('Programs')
foreach ($location in @($desktop, $programs)) {
    if ($location) {
        New-Item -ItemType Directory -Path $location -Force | Out-Null
        $shortcut = $shell.CreateShortcut((Join-Path $location 'Pestinha.lnk'))
        $shortcut.TargetPath = $exe
        $shortcut.Arguments = '--direto'
        $shortcut.WorkingDirectory = $InstallDirectory
        $shortcut.IconLocation = "$exe,0"
        $shortcut.Save()
    }
}
[ordered]@{ repository = 'https://github.com/mille-okws/pestinha'; commit = $commit; exe_sha256 = $expectedHash; installed_at = (Get-Date).ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $InstallDirectory 'installation.json') -Encoding UTF8
Write-Host "Instalado em: $InstallDirectory"
Write-Host "Memoria e configuracoes: $memory"
Write-Host 'Atalhos criados na Area de Trabalho e no menu Iniciar.'
if (-not $NoLaunch) { Start-Process -FilePath $exe -ArgumentList '--direto' -WorkingDirectory $InstallDirectory -WindowStyle Hidden }
