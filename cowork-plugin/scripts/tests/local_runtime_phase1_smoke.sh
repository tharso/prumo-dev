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

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime auth google --help >/dev/null

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
[[ -f "$WORKSPACE/_state/google-integration.json" ]] || fail "google-integration.json nao foi criado"

(
  cd "$WORKSPACE"
  PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime start >"$TMP_DIR/start.out"
)

assert_contains "$TMP_DIR/start.out" "Minha sugestão:" "start nao sugeriu um caminho inicial"
assert_contains "$TMP_DIR/start.out" "Rodar o briefing agora" "start nao ofereceu briefing como porta de entrada"

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime context-dump \
  --workspace "$WORKSPACE" \
  --format json >"$TMP_DIR/context.json"

assert_contains "$TMP_DIR/context.json" "\"user_name\": \"Tharso\"" "context-dump nao expôs user_name"
assert_contains "$TMP_DIR/context.json" "\"core_outdated\": false" "context-dump marcou core outdated sem motivo"
assert_contains "$TMP_DIR/context.json" "\"google_integration\"" "context-dump nao expôs o bloco de integracao Google"
assert_contains "$TMP_DIR/context.json" "\"status\": \"disconnected\"" "integracao Google deveria nascer desconectada"

rm "$WORKSPACE/CLAUDE.md"
rm "$WORKSPACE/_state/briefing-state.json"
rm "$WORKSPACE/_state/google-integration.json"

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime repair \
  --workspace "$WORKSPACE" >"$TMP_DIR/repair.out"

[[ -f "$WORKSPACE/CLAUDE.md" ]] || fail "repair nao recriou CLAUDE.md"
[[ -f "$WORKSPACE/_state/briefing-state.json" ]] || fail "repair nao recriou briefing-state.json"
[[ -f "$WORKSPACE/_state/google-integration.json" ]] || fail "repair nao recriou google-integration.json"

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

mkdir -p "$WORKSPACE/Inbox4Mobile"
cat >"$WORKSPACE/Inbox4Mobile/19 de mar. de 2026, 08:01_text.txt" <<'EOF'
https://youtu.be/QT7W_uHjqWE
EOF

cat >"$TMP_DIR/fake_snapshot.sh" <<'EOF'
#!/usr/bin/env bash
cat <<'OUT'
# Snapshot Google (Prumo Briefing)
## Perfil: pessoal
- GEMINI_CLI_HOME: /tmp/pessoal
- Status: OK
CONTA: batata@example.com
AGENDA_HOJE:
- 20:00-22:00 | pessoal | Jantar de teste
AGENDA_AMANHA:
- nenhum
EMAILS_DESDE_ULTIMO_BRIEFING_TOTAL: 3
TRIAGEM_RESPONDER:
- P1 | 09:30 | Financeiro | Boleto pendente | pagar hoje
TRIAGEM_VER:
- P2 | 10:00 | Produto | Atualizacao de status | leitura rapida
TRIAGEM_SEM_ACAO:
- P3 | 11:00 | News | Newsletter | sem acao
ERROS:
- nenhum
OUT
EOF
chmod +x "$TMP_DIR/fake_snapshot.sh"

PRUMO_RUNTIME_SNAPSHOT_SCRIPT="$TMP_DIR/fake_snapshot.sh" \
PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime snapshot-refresh \
  --workspace "$WORKSPACE" >"$TMP_DIR/snapshot-refresh.out"

assert_contains "$TMP_DIR/snapshot-refresh.out" "perfis ok: 1" "snapshot-refresh nao conseguiu atualizar o cache"
[[ -f "$WORKSPACE/_state/google-dual-snapshot.json" ]] || fail "snapshot-refresh nao persistiu cache do snapshot dual"

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime briefing \
  --workspace "$WORKSPACE" >"$TMP_DIR/briefing.out"

assert_contains "$TMP_DIR/briefing.out" "1. Preflight:" "briefing nao começou com preflight numerado"
assert_contains "$TMP_DIR/briefing.out" "2. Google:" "briefing nao trouxe status da integracao Google"
assert_contains "$TMP_DIR/briefing.out" "3. Apple Reminders:" "briefing nao trouxe status de Apple Reminders"
assert_contains "$TMP_DIR/briefing.out" "4. Agenda:" "briefing nao trouxe agenda consolidada"
assert_contains "$TMP_DIR/briefing.out" "Jantar de teste" "briefing nao incorporou snapshot dual"
assert_contains "$TMP_DIR/briefing.out" "5. Inbox mobile:" "briefing nao trouxe bloco de inbox mobile"
assert_contains "$TMP_DIR/briefing.out" "inbox-preview.html" "briefing nao linkou o preview do inbox"
assert_contains "$TMP_DIR/briefing.out" "6. Emails:" "briefing nao trouxe bloco de emails"
assert_contains "$TMP_DIR/briefing.out" "Responder: 1" "briefing nao resumiu a triagem de emails"
assert_contains "$TMP_DIR/briefing.out" "snapshot dual reaproveitado do cache local" "briefing nao preferiu o cache local"
assert_contains "$TMP_DIR/briefing.out" "7. Panorama local:" "briefing nao trouxe panorama local"
assert_contains "$TMP_DIR/briefing.out" "8. Proposta do dia:" "briefing nao chegou ao bloco final com numeracao continua"
assert_contains "$TMP_DIR/briefing.out" "a) Aceitar e seguir" "briefing nao ofereceu a opcao a)"
assert_contains "$TMP_DIR/briefing.out" "d) Tá bom por hoje" "briefing nao ofereceu a opcao d)"

echo "ok: local runtime phase1 smoke"
