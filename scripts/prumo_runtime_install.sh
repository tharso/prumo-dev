#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Instalando runtime local do Prumo"
echo "Repo: $ROOT_DIR"

python3 -m pip install --user -e "$ROOT_DIR"

echo ""
echo "Runtime instalado."
echo "Teste rapido:"
echo "1. prumo --version"
echo "2. prumo setup --workspace /caminho/do/workspace"
