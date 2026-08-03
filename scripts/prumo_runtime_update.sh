#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$ROOT_DIR/VERSION")"

find_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  if [ -x "$HOME/.local/bin/uv" ]; then
    echo "$HOME/.local/bin/uv"
    return 0
  fi
  return 1
}

find_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

echo "==> Atualizando runtime local do Prumo"
echo "Repo: $ROOT_DIR"

if UV_BIN="$(find_uv)"; then
  echo "Usando uv: $UV_BIN"
  # Sem pin de versão: o uv honra o requires-python do pyproject (>=3.10) — #301
  "$UV_BIN" tool install --editable --force "$ROOT_DIR"
elif PYTHON_BIN="$(find_python)"; then
  echo "uv nao encontrado. Vou de pip com $PYTHON_BIN"
  "$PYTHON_BIN" -m pip install --user -e "$ROOT_DIR"
else
  echo "erro: preciso de uv ou Python 3.10+ para atualizar o runtime." >&2
  echo "Instale uv (https://docs.astral.sh/uv/) ou um Python 3.10+ e tente de novo." >&2
  exit 1
fi

echo ""
echo "Runtime atualizado. Versao: $VERSION"
echo "Se o host estiver aberto, reinicie antes de testar."
