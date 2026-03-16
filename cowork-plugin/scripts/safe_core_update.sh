#!/usr/bin/env bash
set -euo pipefail

# Safe updater for Prumo core.
# Writes only:
# 1) PRUMO-CORE.md
# 2) _backup/PRUMO-CORE.md.*

REPO_DIR="${1:-.}"
REMOTE_CORE_URL="${2:-https://raw.githubusercontent.com/tharso/prumo/main/cowork-plugin/skills/prumo/references/prumo-core.md}"
TARGET_FILE="${REPO_DIR}/PRUMO-CORE.md"
BACKUP_DIR="${REPO_DIR}/_backup"
TIMESTAMP="$(date +"%Y-%m-%d-%H%M%S")"
BACKUP_FILE="${BACKUP_DIR}/PRUMO-CORE.md.${TIMESTAMP}"

if [[ ! -f "$TARGET_FILE" ]]; then
  echo "Erro: $TARGET_FILE não encontrado." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$TARGET_FILE" "$BACKUP_FILE"

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT
curl -fsSL "$REMOTE_CORE_URL" > "$TMP_FILE"

if [[ ! -s "$TMP_FILE" ]]; then
  echo "Erro: conteúdo remoto vazio. Update abortado." >&2
  exit 1
fi

if ! grep -q "^## Changelog do Core" "$TMP_FILE"; then
  echo "Erro: core remoto incompleto (sem changelog). Update abortado." >&2
  exit 1
fi

if ! grep -Eq '^\*Prumo Core v[0-9]+\.[0-9]+\.[0-9]+ — https://github\.com/tharso/prumo\*$' "$TMP_FILE"; then
  echo "Erro: core remoto incompleto (sem rodapé de integridade). Update abortado." >&2
  exit 1
fi

mv "$TMP_FILE" "$TARGET_FILE"

echo "Update concluído com segurança."
echo "Backup: $BACKUP_FILE"
