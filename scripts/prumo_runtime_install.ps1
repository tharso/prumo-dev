$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$Version = Get-Content (Join-Path $RootDir "VERSION") -Raw
$Version = $Version.Trim()

$PackageManager = ""
$PythonUsed = ""
$SourceKind = "editable"

function Find-Uv {
  $uv = Get-Command uv -ErrorAction SilentlyContinue
  if ($uv) {
    return $uv.Source
  }
  $candidate = Join-Path $HOME ".local\bin\uv.exe"
  if (Test-Path $candidate) {
    return $candidate
  }
  return $null
}

function Find-Python {
  foreach ($candidate in @("py", "python", "python3")) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
      return $command.Source
    }
  }
  return $null
}

function Write-InstallMarker {
  $markerDir = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "prumo" } else { Join-Path $HOME "AppData\Local\prumo" }
  $markerPath = Join-Path $markerDir "install-method.json"
  $prumoExe = (Get-Command prumo -ErrorAction SilentlyContinue).Source
  if (-not $prumoExe) { $prumoExe = "unknown" }
  $installedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

  if (-not (Test-Path $markerDir)) {
    New-Item -ItemType Directory -Path $markerDir -Force | Out-Null
  }

  $marker = @{
    schema_version = "1.0"
    installed_version = $Version
    installed_at = $installedAt
    launcher = "install-script"
    package_manager = $script:PackageManager
    source_kind = $script:SourceKind
    source = "local-checkout"
    python = $script:PythonUsed
    prumo_executable = $prumoExe
  } | ConvertTo-Json -Depth 2

  Set-Content -Path $markerPath -Value $marker -Encoding utf8
  Write-Host "Marker gravado em: $markerPath"
}

Write-Host "==> Instalando runtime local do Prumo"
Write-Host "Repo: $RootDir"

$UvBin = Find-Uv
if ($UvBin) {
  Write-Host "Usando uv: $UvBin"
  $script:PackageManager = "uv-tool"
  $script:PythonUsed = "uv-managed"
  & $UvBin tool install --editable --force --python 3.11 $RootDir
}
else {
  $PythonBin = Find-Python
  if (-not $PythonBin) {
    Write-Error "Preciso de uv ou Python 3.11+ para instalar o runtime. Instale um deles e tente de novo."
  }
  Write-Host "uv nao encontrado. Vou de pip com $PythonBin"
  $script:PackageManager = "pip-user"
  $script:PythonUsed = $PythonBin
  if ((Split-Path $PythonBin -Leaf).ToLower() -eq "py.exe" -or (Split-Path $PythonBin -Leaf).ToLower() -eq "py") {
    & $PythonBin -3.11 -m pip install --user -e $RootDir
  }
  else {
    & $PythonBin -m pip install --user -e $RootDir
  }
}

Write-InstallMarker

Write-Host ""
Write-Host "Runtime instalado. Versao: $Version"
Write-Host "Se o comando 'prumo' nao aparecer de primeira, feche e abra o terminal antes de xingar o Windows."
Write-Host "Teste rapido:"
Write-Host "1. prumo --version"
Write-Host "2. prumo setup --workspace C:\caminho\do\workspace"
