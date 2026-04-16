#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=""
VERSION=""
INSTALL_MODE="editable"
TEMP_SOURCE_DIR=""
ARCHIVE_URL="${PRUMO_INSTALL_ARCHIVE_URL:-https://github.com/tharso/prumo/archive/refs/heads/main.tar.gz}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "erro: dependência ausente: $1" >&2
    exit 1
  fi
}

cleanup() {
  if [ -n "$TEMP_SOURCE_DIR" ] && [ -d "$TEMP_SOURCE_DIR" ]; then
    rm -rf "$TEMP_SOURCE_DIR"
  fi
}

trap cleanup EXIT

bootstrap_source_archive() {
  need_cmd curl
  need_cmd tar
  TEMP_SOURCE_DIR="$(mktemp -d)"
  local archive_path="$TEMP_SOURCE_DIR/prumo.tar.gz"
  echo "Repo local não encontrado. Vou baixar um snapshot do repositório para instalar o runtime."
  echo "Archive: $ARCHIVE_URL"
  curl -fsSL --proto =https --tlsv1.2 "$ARCHIVE_URL" -o "$archive_path"
  tar -xzf "$archive_path" -C "$TEMP_SOURCE_DIR"
  ROOT_DIR="$(find "$TEMP_SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d -name 'prumo-*' | head -n 1)"
  if [ -z "$ROOT_DIR" ] || [ ! -f "$ROOT_DIR/VERSION" ] || [ ! -f "$ROOT_DIR/pyproject.toml" ]; then
    echo "erro: baixei o snapshot, mas ele não parece um checkout válido do Prumo." >&2
    exit 1
  fi
  INSTALL_MODE="archive"
}

resolve_root_dir() {
  if [ -n "${PRUMO_INSTALL_ROOT_DIR:-}" ] && [ -f "${PRUMO_INSTALL_ROOT_DIR}/VERSION" ] && [ -f "${PRUMO_INSTALL_ROOT_DIR}/pyproject.toml" ]; then
    ROOT_DIR="$(cd "${PRUMO_INSTALL_ROOT_DIR}" && pwd)"
    INSTALL_MODE="editable"
    return 0
  fi

  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local candidate_root
  candidate_root="$(cd "${script_dir}/.." && pwd)"

  if [ -f "${candidate_root}/VERSION" ] && [ -f "${candidate_root}/pyproject.toml" ]; then
    ROOT_DIR="$candidate_root"
    INSTALL_MODE="editable"
    return 0
  fi

  bootstrap_source_archive
}

resolve_root_dir
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
  for candidate in python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

echo "==> Instalando runtime local do Prumo"
echo "Repo: $ROOT_DIR"
echo "Modo de instalação: $INSTALL_MODE"

if UV_BIN="$(find_uv)"; then
  echo "Usando uv: $UV_BIN"
  if [ "$INSTALL_MODE" = "editable" ]; then
    "$UV_BIN" tool install --editable --force --python 3.11 "$ROOT_DIR"
  else
    "$UV_BIN" tool install --force --python 3.11 "$ROOT_DIR"
  fi
elif PYTHON_BIN="$(find_python)"; then
  echo "uv nao encontrado. Vou de pip com $PYTHON_BIN"
  if [ "$INSTALL_MODE" = "editable" ]; then
    "$PYTHON_BIN" -m pip install --user -e "$ROOT_DIR"
  else
    "$PYTHON_BIN" -m pip install --user "$ROOT_DIR"
  fi
else
  echo "erro: preciso de uv ou Python 3.11+ para instalar o runtime." >&2
  echo "Instale uv (https://docs.astral.sh/uv/) ou um Python 3.11+ e tente de novo." >&2
  exit 1
fi

echo ""
echo "Runtime instalado. Versao: $VERSION"
if [ "$INSTALL_MODE" = "archive" ]; then
  echo "Obs: esta instalação veio de um snapshot do repositório, não de um checkout editável."
  echo "Se você for desenvolver no runtime, clone o repo e rode este script a partir do checkout local."
fi
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  echo "Obs: \$HOME/.local/bin nao esta no PATH desta sessao."
  echo "Se o comando \`prumo\` nao responder, rode: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
echo "Teste rapido:"
echo "1. prumo --version"
echo "2. prumo setup --workspace /caminho/do/workspace"
