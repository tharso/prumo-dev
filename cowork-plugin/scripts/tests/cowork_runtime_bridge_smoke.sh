#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TMP_DIR="$(mktemp -d)"
WORKSPACE_OK="$TMP_DIR/ws-ok"
WORKSPACE_OLD="$TMP_DIR/ws-old"

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

mkdir -p "$WORKSPACE_OK" "$WORKSPACE_OLD"

cat >"$WORKSPACE_OLD/CLAUDE.md" <<'EOF'
# legado
EOF

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime setup \
  --workspace "$WORKSPACE_OK" \
  --user-name "Tharso" \
  --agent-name "Prumo" \
  --timezone "America/Sao_Paulo" \
  --briefing-time "09:00" >/dev/null

cat >"$WORKSPACE_OK/PAUTA.md" <<'EOF'
# Pauta

## Quente (precisa de atenção agora)

- [Produto] Fechar o bridge do Cowork.

## Em andamento

- [Produto] Validar runtime local.

## Agendado / Lembretes

- **21/03**: [Saúde] Agendar exame.
EOF

cat >"$WORKSPACE_OK/INBOX.md" <<'EOF'
# Inbox

- [Email] Responder contador.
EOF

PRUMO_BRIDGE_PREFER_REPO=1 python3 "$ROOT_DIR/scripts/prumo_cowork_bridge.py" \
  --workspace "$WORKSPACE_OK" \
  --command start >"$TMP_DIR/start-ok.out"

assert_contains "$TMP_DIR/start-ok.out" "Minha sugestão:" "bridge nao devolveu a porta de entrada do runtime"
assert_contains "$TMP_DIR/start-ok.out" "Rodar o briefing agora" "bridge start nao ofereceu briefing"

PRUMO_BRIDGE_PREFER_REPO=1 PRUMO_RUNTIME_DISABLE_SNAPSHOT=1 python3 "$ROOT_DIR/scripts/prumo_cowork_bridge.py" \
  --workspace "$WORKSPACE_OK" \
  --command briefing >"$TMP_DIR/bridge-ok.out"

assert_contains "$TMP_DIR/bridge-ok.out" "1. Preflight:" "bridge nao devolveu saida do runtime"
assert_contains "$TMP_DIR/bridge-ok.out" "2. Google:" "bridge nao trouxe status da integracao Google"
assert_contains "$TMP_DIR/bridge-ok.out" "Proposta do dia:" "bridge nao manteve briefing completo"

set +e
PRUMO_BRIDGE_PREFER_REPO=1 python3 "$ROOT_DIR/scripts/prumo_cowork_bridge.py" \
  --workspace "$WORKSPACE_OLD" \
  --command start >"$TMP_DIR/start-old.out" 2>"$TMP_DIR/start-old.err"
STATUS="$?"
set -e

[[ "$STATUS" -eq 0 ]] || fail "bridge start deveria funcionar ate em workspace legado"
assert_contains "$TMP_DIR/start-old.out" "migrate" "bridge start nao sugeriu migrate no workspace legado"

set +e
PRUMO_BRIDGE_PREFER_REPO=1 python3 "$ROOT_DIR/scripts/prumo_cowork_bridge.py" \
  --workspace "$WORKSPACE_OLD" \
  --command briefing >"$TMP_DIR/bridge-old.out" 2>"$TMP_DIR/bridge-old.err"
STATUS="$?"
set -e

[[ "$STATUS" -eq 12 ]] || fail "bridge deveria cair com codigo 12 em workspace antigo"
assert_contains "$TMP_DIR/bridge-old.err" "bridge-disabled:" "bridge nao explicou fallback legado"

echo "ok: cowork runtime bridge smoke"
