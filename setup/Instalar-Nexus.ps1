[CmdletBinding()]
param(
    [string]$PythonExecutable,
    [string]$EnvironmentDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Codex\runtimes\nexus'),
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'Programs\Nexus'),
    [switch]$EnableVoice,
    [switch]$NoLaunch
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::Is64BitOperatingSystem) { throw 'Requer Windows de 64 bits.' }
$root = Split-Path $PSScriptRoot -Parent
$existing = @(Get-Process -Name Nexus -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith([IO.Path]::GetFullPath($InstallDirectory) + '\', [StringComparison]::OrdinalIgnoreCase) })
if ($existing.Count) { throw 'Feche o Nexus pelo menu Sair antes de reinstalar.' }
if (-not $PythonExecutable) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $PythonExecutable = (& $launcher.Source -3 -c 'import sys; print(sys.executable)')
        if ($LASTEXITCODE -ne 0) { throw 'Instale Python 3.11 ou superior de 64 bits.' }
    } else {
        $command = Get-Command python -ErrorAction SilentlyContinue
        if ($command) { $PythonExecutable = $command.Source }
    }
}
if (-not $PythonExecutable) { throw 'Instale Python 3.11+ ou informe -PythonExecutable.' }
& $PythonExecutable -c 'import sys,struct; assert sys.version_info >= (3,11) and struct.calcsize("P")==8, "Requer Python 3.11+ de 64 bits"'
if ($LASTEXITCODE -ne 0) { throw 'Python incompativel.' }
$runtime = Join-Path $EnvironmentDirectory 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtime)) {
    & $PythonExecutable -m venv $EnvironmentDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel criar o ambiente Python.' }
}
Push-Location $root
try {
    & $runtime -m pip install 'PySide6==6.11.3' -r requirements.txt -r requirements-voice.txt 'pyinstaller==6.22.3'
    if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependencias.' }
    & $runtime setup/Preparar-Voz.py
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar o modelo.' }
    # Evita capturar DLLs de outras ferramentas (por exemplo ICU do Poppler) pelo PATH.
    $previousPath = $env:PATH
    try {
        $env:PATH = ((Split-Path $runtime -Parent), (Join-Path $EnvironmentDirectory 'Lib\site-packages\PySide6'), "$env:SystemRoot\System32", $env:SystemRoot) -join ';'
        & $runtime -m PyInstaller --clean --noconfirm --onedir --windowed --name Nexus --distpath build/nexus --workpath build/nexus-work --specpath build --hidden-import win32timezone --collect-all vosk --collect-all sounddevice main.py
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar Nexus.' }
    } finally {
        $env:PATH = $previousPath
    }
    New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
    # Uma atualizacao nao pode deixar DLLs antigas misturadas com o pacote novo.
    $internal = Join-Path ([IO.Path]::GetFullPath($InstallDirectory)) '_internal'
    if (Test-Path -LiteralPath $internal) {
        $resolvedInternal = (Resolve-Path -LiteralPath $internal).Path
        if (-not $resolvedInternal.Equals($internal, [StringComparison]::OrdinalIgnoreCase)) { throw 'Caminho de bibliotecas inesperado.' }
        Move-Item -LiteralPath $resolvedInternal -Destination ($internal + '.backup-' + [guid]::NewGuid().ToString('N'))
    }
    Get-ChildItem -LiteralPath (Join-Path $root 'build\nexus\Nexus') -Force | Copy-Item -Destination $InstallDirectory -Recurse -Force
    foreach ($folder in @('assets','pets','models')) {
        $destination = Join-Path $InstallDirectory $folder
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        Get-ChildItem -LiteralPath (Join-Path $root $folder) -Force | Copy-Item -Destination $destination -Recurse -Force
    }
    foreach ($file in @('LICENSE','README.md','PRIVACIDADE.md','MEU-PROJETO.md')) {
        Copy-Item -LiteralPath (Join-Path $root $file) -Destination $InstallDirectory -Force
    }
    $permissionFile = Join-Path $InstallDirectory 'memory\permissions.json'
    New-Item -ItemType Directory -Path (Split-Path $permissionFile -Parent) -Force | Out-Null
    if (Test-Path -LiteralPath $permissionFile) {
        $settings = Get-Content -LiteralPath $permissionFile -Raw | ConvertFrom-Json
    } else {
        $defaultJson = & $runtime -c 'import json; from pestinha.config import DEFAULT_PERMISSIONS; print(json.dumps(DEFAULT_PERMISSIONS))'
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel preparar configuracoes.' }
        $settings = $defaultJson | ConvertFrom-Json
    }
    if ($EnableVoice) {
        $settings | Add-Member -NotePropertyName ouvir_nome -NotePropertyValue $true -Force
        $settings | Add-Member -NotePropertyName resposta_voz -NotePropertyValue $true -Force
    }
    [IO.File]::WriteAllText($permissionFile, ($settings | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
    $exe = Join-Path $InstallDirectory 'Nexus.exe'
    $shell = New-Object -ComObject WScript.Shell
    foreach ($location in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
        if ($location) {
            New-Item -ItemType Directory -Path $location -Force | Out-Null
            $shortcut = $shell.CreateShortcut((Join-Path $location 'Nexus.lnk'))
            $shortcut.TargetPath = $exe
            $shortcut.Arguments = '--direto'
            $shortcut.WorkingDirectory = $InstallDirectory
            $shortcut.IconLocation = "$exe,0"
            $shortcut.Save()
        }
    }
    Write-Host "Nexus instalado em $InstallDirectory"
    if (-not $NoLaunch) { Start-Process -FilePath $exe -ArgumentList '--direto' -WorkingDirectory $InstallDirectory -WindowStyle Hidden }
} finally {
    Pop-Location
}
