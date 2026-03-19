#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TMP_DIR="$(mktemp -d)"
WORKSPACE="$TMP_DIR/legacy"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

assert_contains() {
  local file="$1"
  local needle="$2"
  local message="$3"
  grep -Fq "$needle" "$file" || fail "$message"
}

mkdir -p "$WORKSPACE/_state" "$WORKSPACE/Referencias"

cat >"$WORKSPACE/CLAUDE.md" <<'EOF'
# Prumo — Tharso

- Nome preferido: Tharso
- Fuso: America/Sao_Paulo

## Lembretes recorrentes

- Passaporte 23/02
EOF

cat >"$WORKSPACE/PRUMO-CORE.md" <<'EOF'
# Prumo Core — Motor do sistema

> **prumo_version: 4.5.0**
EOF

cat >"$WORKSPACE/PAUTA.md" <<'EOF'
# Pauta

## Em andamento

- [Produto] Fechar migracao.
EOF

cat >"$WORKSPACE/INBOX.md" <<'EOF'
# Inbox

_Inbox limpo._
EOF

cat >"$WORKSPACE/REGISTRO.md" <<'EOF'
# Registro

| Data | Origem | Resumo | Ação | Destino |
|------|--------|--------|------|---------|
EOF

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime migrate \
  --workspace "$WORKSPACE" >"$TMP_DIR/migrate.out"

[[ -f "$WORKSPACE/AGENT.md" ]] || fail "migrate nao criou AGENT.md"
[[ -f "$WORKSPACE/_state/workspace-schema.json" ]] || fail "migrate nao criou workspace-schema.json"
[[ -f "$WORKSPACE/Agente/LEGADO-CLAUDE.md" ]] || fail "migrate nao preservou CLAUDE legado"

assert_contains "$WORKSPACE/CLAUDE.md" 'Leia `AGENT.md` primeiro.' "migrate nao reescreveu CLAUDE.md como wrapper"
assert_contains "$WORKSPACE/PRUMO-CORE.md" "prumo_version: 4.9.0" "migrate nao atualizou PRUMO-CORE.md"
assert_contains "$WORKSPACE/Agente/LEGADO-CLAUDE.md" "Passaporte 23/02" "migrate nao importou conteudo legado do CLAUDE"

BACKUP_ROOT="$(find "$WORKSPACE/_backup/runtime-migrate" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[[ -n "$BACKUP_ROOT" ]] || fail "migrate nao criou backup"
[[ -f "$BACKUP_ROOT/CLAUDE.md" ]] || fail "migrate nao guardou backup do CLAUDE"
[[ -f "$BACKUP_ROOT/PRUMO-CORE.md" ]] || fail "migrate nao guardou backup do core"

assert_contains "$TMP_DIR/migrate.out" "sobrescrito com backup: CLAUDE.md" "migrate nao reportou sobrescrita do CLAUDE"
assert_contains "$TMP_DIR/migrate.out" "sobrescrito com backup: PRUMO-CORE.md" "migrate nao reportou sobrescrita do core"

echo "ok: local runtime migrate smoke"
