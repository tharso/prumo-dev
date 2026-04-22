$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$Version = Get-Content (Join-Path $RootDir "VERSION") -Raw
$Version = $Version.Trim()

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

Write-Host "==> Instalando runtime local do Prumo"
Write-Host "Repo: $RootDir"

$UvBin = Find-Uv
if ($UvBin) {
  Write-Host "Usando uv: $UvBin"
  & $UvBin tool install --editable --force --python 3.11 $RootDir
}
else {
  $PythonBin = Find-Python
  if (-not $PythonBin) {
    Write-Error "Preciso de uv ou Python 3.11+ para instalar o runtime. Instale um deles e tente de novo."
  }
  Write-Host "uv não encontrado. Vou de pip com $PythonBin"
  if ((Split-Path $PythonBin -Leaf).ToLower() -eq "py.exe" -or (Split-Path $PythonBin -Leaf).ToLower() -eq "py") {
    & $PythonBin -3.11 -m pip install --user -e $RootDir
  }
  else {
    & $PythonBin -m pip install --user -e $RootDir
  }
}

Write-Host ""
Write-Host "Runtime instalado. Versão: $Version"
Write-Host "Se o comando 'prumo' não aparecer de primeira, feche e abra o terminal antes de xingar o Windows."
Write-Host "Teste rápido:"
Write-Host "1. prumo --version"
Write-Host "2. prumo setup --workspace C:\caminho\do\workspace"
