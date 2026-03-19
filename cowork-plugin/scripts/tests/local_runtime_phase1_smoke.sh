#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TMP_DIR="$(mktemp -d)"
WORKSPACE="$TMP_DIR/ws"

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

mkdir -p "$WORKSPACE"

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime setup \
  --workspace "$WORKSPACE" \
  --user-name "Tharso" \
  --agent-name "Prumo" \
  --timezone "America/Sao_Paulo" \
  --briefing-time "09:00" >"$TMP_DIR/setup.out"

[[ -f "$WORKSPACE/AGENT.md" ]] || fail "AGENT.md nao foi criado"
[[ -f "$WORKSPACE/CLAUDE.md" ]] || fail "CLAUDE.md nao foi criado"
[[ -f "$WORKSPACE/AGENTS.md" ]] || fail "AGENTS.md nao foi criado"
[[ -f "$WORKSPACE/PRUMO-CORE.md" ]] || fail "PRUMO-CORE.md nao foi criado"
[[ -f "$WORKSPACE/Agente/INDEX.md" ]] || fail "Agente/INDEX.md nao foi criado"
[[ -f "$WORKSPACE/_state/workspace-schema.json" ]] || fail "workspace-schema.json nao foi criado"

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime context-dump \
  --workspace "$WORKSPACE" \
  --format json >"$TMP_DIR/context.json"

assert_contains "$TMP_DIR/context.json" "\"user_name\": \"Tharso\"" "context-dump nao expôs user_name"
assert_contains "$TMP_DIR/context.json" "\"core_outdated\": false" "context-dump marcou core outdated sem motivo"

rm "$WORKSPACE/CLAUDE.md"
rm "$WORKSPACE/_state/briefing-state.json"

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime repair \
  --workspace "$WORKSPACE" >"$TMP_DIR/repair.out"

[[ -f "$WORKSPACE/CLAUDE.md" ]] || fail "repair nao recriou CLAUDE.md"
[[ -f "$WORKSPACE/_state/briefing-state.json" ]] || fail "repair nao recriou briefing-state.json"

cat >"$WORKSPACE/PAUTA.md" <<'EOF'
# Pauta

## Quente (precisa de atenção agora)

- [Infra] Atualizar DNS da Brise hoje.

## Em andamento

- [Produto] Consolidar plano da Fase 1.

## Agendado / Lembretes

- **21/03**: [Saúde] Agendar exame.
EOF

cat >"$WORKSPACE/INBOX.md" <<'EOF'
# Inbox

- [Email] Responder fornecedor.
EOF

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime briefing \
  --workspace "$WORKSPACE" >"$TMP_DIR/briefing.out"

assert_contains "$TMP_DIR/briefing.out" "1. Preflight:" "briefing nao começou com preflight numerado"
assert_contains "$TMP_DIR/briefing.out" "2. Quente:" "briefing nao manteve numeracao continua"
assert_contains "$TMP_DIR/briefing.out" "6. Proposta do dia:" "briefing nao chegou ao bloco final com numeracao continua"
assert_contains "$TMP_DIR/briefing.out" "a) ver a pauta detalhada" "briefing nao ofereceu alternativas"

echo "ok: local runtime phase1 smoke"
