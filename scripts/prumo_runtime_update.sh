#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Atualizando runtime local do Prumo"
echo "Repo: $ROOT_DIR"

python3 -m pip install --user -e "$ROOT_DIR"

echo ""
echo "Runtime atualizado."
echo "Se o host estiver aberto, reinicie antes de testar."
