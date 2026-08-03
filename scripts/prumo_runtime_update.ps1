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
  # Interpretador ATIVO do ambiente primeiro, e só se for 3.10+ (senão um
  # python 3.9 no PATH seria aceito e o launcher válido nunca tentado); o py
  # launcher por último — ele escolhe versão própria, e os Scripts dela
  # podem não estar no PATH (#301)
  foreach ($candidate in @("python", "python3")) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
      & $command.Source -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
      if ($LASTEXITCODE -eq 0) {
        return $command.Source
      }
    }
  }
  $py = Get-Command "py" -ErrorAction SilentlyContinue
  if ($py) {
    return $py.Source
  }
  return $null
}

Write-Host "==> Atualizando runtime local do Prumo"
Write-Host "Repo: $RootDir"

$UvBin = Find-Uv
if ($UvBin) {
  Write-Host "Usando uv: $UvBin"
  # Sem pin de versao: o uv honra o requires-python do pyproject (>=3.10) — #301
  & $UvBin tool install --editable --force $RootDir
}
else {
  $PythonBin = Find-Python
  if (-not $PythonBin) {
    Write-Error "Preciso de uv ou Python 3.10+ para atualizar o runtime. Instale um deles e tente de novo."
  }
  Write-Host "uv não encontrado. Vou de pip com $PythonBin"
  if ((Split-Path $PythonBin -Leaf).ToLower() -eq "py.exe" -or (Split-Path $PythonBin -Leaf).ToLower() -eq "py") {
    $PyVersion = $null
    foreach ($v in @("3.13", "3.12", "3.11", "3.10")) {
      & $PythonBin "-$v" -c "pass" 2>$null
      if ($LASTEXITCODE -eq 0) { $PyVersion = $v; break }
    }
    if (-not $PyVersion) {
      Write-Error "Nenhum Python 3.10+ registrado no py launcher. Instale um e tente de novo."
    }
    & $PythonBin "-$PyVersion" -m pip install --user -e $RootDir
  }
  else {
    & $PythonBin -m pip install --user -e $RootDir
  }
}

Write-Host ""
Write-Host "Runtime atualizado. Versão: $Version"
Write-Host "Se o host estiver aberto, reinicie antes de testar. Windows adora fingir que ouviu, mas às vezes só assentiu."
