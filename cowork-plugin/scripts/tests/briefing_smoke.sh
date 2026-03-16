#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
REPO_ROOT="$(cd -- "$ROOT_DIR/.." && pwd)"

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

assert_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if command -v rg >/dev/null 2>&1; then
    rg -q --pcre2 -- "$pattern" "$file" || fail "$label (arquivo: $file)"
    return 0
  fi

  if ! grep -Eq -- "$pattern" "$file"; then
    fail "$label (arquivo: $file)"
  fi
}

CORE_FILE=""
if [[ -f "skills/prumo/references/prumo-core.md" ]]; then
  CORE_FILE="skills/prumo/references/prumo-core.md"
elif [[ -f "references/prumo-core.md" ]]; then
  CORE_FILE="references/prumo-core.md"
fi
SKILL_FILE="skills/briefing/SKILL.md"
SKILL_MIRROR_FILE="skills-briefing-SKILL.md"
TEMPLATES_FILE=""
if [[ -f "skills/prumo/references/file-templates.md" ]]; then
  TEMPLATES_FILE="skills/prumo/references/file-templates.md"
elif [[ -f "references/file-templates.md" ]]; then
  TEMPLATES_FILE="references/file-templates.md"
fi
VERSION_FILE="VERSION"

for file in "$CORE_FILE" "$SKILL_FILE" "$TEMPLATES_FILE" "$VERSION_FILE"; do
  [[ -f "$file" ]] || fail "Arquivo obrigatório ausente: $file"
done

BRIEFING_FILES=("$CORE_FILE" "$SKILL_FILE")
if [[ -f "$SKILL_MIRROR_FILE" ]]; then
  BRIEFING_FILES+=("$SKILL_MIRROR_FILE")
fi

VERSION_VALUE="$(cat "$VERSION_FILE")"
CORE_VERSION="$(grep -Eo '^> \*\*prumo_version: [0-9]+\.[0-9]+\.[0-9]+\*\*$' "$CORE_FILE" | sed -E 's/^> \*\*prumo_version: ([0-9]+\.[0-9]+\.[0-9]+)\*\*$/\1/' | head -n1)"
[[ -n "$CORE_VERSION" ]] || fail "Não foi possível extrair prumo_version do core"
[[ "$VERSION_VALUE" == "$CORE_VERSION" ]] || fail "Divergência de versão: VERSION=$VERSION_VALUE vs prumo_version=$CORE_VERSION"
assert_contains "$CORE_FILE" "^### v$CORE_VERSION \\(" "Changelog do core não contém seção da versão atual"

for file in "${BRIEFING_FILES[@]}"; do
  assert_contains "$file" "Responder" "Taxonomia: ausência de 'Responder'"
  assert_contains "$file" "Ver" "Taxonomia: ausência de 'Ver'"
  assert_contains "$file" "Sem ação|Sem acao" "Taxonomia: ausência de 'Sem ação'"
  assert_contains "$file" "P1/P2/P3|P1.*P2.*P3" "Prioridade P1/P2/P3 ausente"
done

for file in "${BRIEFING_FILES[@]}"; do
  assert_contains "$file" "last_briefing_at" "Janela temporal: falta referência a last_briefing_at"
  assert_contains "$file" "24h|24 h|24 horas" "Janela temporal: falta fallback de 24h"
  assert_contains "$file" "captur.*memória|usar esse valor como janela desta sessão" "Janela temporal: falta snapshot do valor anterior"
done

for file in "${BRIEFING_FILES[@]}"; do
  assert_contains "$file" "Não depende de script externo|Não depende de nenhum script externo|prumo_briefing_state\\.py" "Persistência direta: regra obrigatória ausente"
  assert_contains "$file" "antes da primeira resposta.*last_briefing_at|persistir o início do briefing do dia" "Persistência direta: gravação no início ausente"
  assert_contains "$file" "briefing iniciado/concluído: confirmar que .*last_briefing_at|Se briefing iniciou/concluiu, .*last_briefing_at" "Persistência direta: validação de briefing iniciado/concluído ausente"
  assert_contains "$file" "briefing interrompido: confirmar que .*interrupted_at|Se briefing foi interrompido, .*interrupted_at" "Persistência direta: validação de briefing interrompido ausente"
done

for file in "${BRIEFING_FILES[@]}"; do
  assert_contains "$file" "Nunca usar WebFetch|Nunca use WebFetch" "Update seguro: proibição explícita de WebFetch ausente"
  assert_contains "$file" "não consegue baixar o core bruto com segurança|não bloquear o briefing" "Update seguro: fallback para runtime sem transporte ausente"
  assert_contains "$file" "transporte seguro de aplicação" "Update seguro: separação entre detectar e aplicar ausente"
  assert_contains "$file" "Nunca buscar changelog remoto via WebFetch|sem changelog detalhado|nova versão do motor" "Update seguro: fallback sem changelog remoto ausente"
done

for file in "${BRIEFING_FILES[@]}"; do
  if command -v rg >/dev/null 2>&1; then
    ! rg -q --fixed-strings -- "--mark-briefing-complete" "$file" || fail "Persistência direta: referência legada a --mark-briefing-complete ainda presente em $file"
  elif grep -Fq -- "--mark-briefing-complete" "$file"; then
    fail "Persistência direta: referência legada a --mark-briefing-complete ainda presente em $file"
  fi
done

for file in "${BRIEFING_FILES[@]}"; do
  assert_contains "$file" "_preview-index\\.json" "Preview adoption: falta referência ao índice de preview"
  assert_contains "$file" "DEVE linkar|deve ser linkado|link obrigatório" "Preview adoption: regra bloqueante de link ausente"
  assert_contains "$file" "inbox-preview\\.html" "Preview adoption: referência ao html de preview ausente"
  assert_contains "$file" "regenerar SEMPRE|regenerar .*inbox-preview|No início de todo briefing diário, regenerar" "Preview adoption: falta regra de regeneração no início"
  assert_contains "$file" "primeira interação.*proibido abrir|na primeira resposta do briefing, é proibido abrir" "Preview adoption: falta guardrail da primeira interação"
done

for file in "${BRIEFING_FILES[@]}"; do
  assert_contains "$file" "Bloco 1" "Briefing progressivo: ausência de Bloco 1"
  assert_contains "$file" "Bloco 2" "Briefing progressivo: ausência de Bloco 2"
  assert_contains "$file" "Tá bom por hoje|tá bom por hoje|escape|depois" "Escape hatch: gatilhos ausentes"
  assert_contains "$file" "interrupted_at" "Escape hatch: ausência de interrupted_at"
  assert_contains "$file" "resume_point" "Escape hatch: ausência de resume_point"
  assert_contains "$file" "--detalhe|briefing --detalhe" "Modo detalhe: ausência de gatilho explícito"
  assert_contains "$file" "\\| cobrar: DD/MM|cobrar: DD/MM" "Supressão temporal: formato cobrar não documentado"
done

assert_contains "$TEMPLATES_FILE" "interrupted_at" "Template de briefing-state sem interrupted_at"
assert_contains "$TEMPLATES_FILE" "resume_point" "Template de briefing-state sem resume_point"
assert_contains "$TEMPLATES_FILE" "\\| cobrar: 25/02|cobrar: DD/MM" "Template de pauta sem exemplo de cobrança"

assert_contains "$SKILL_FILE" "Google dual via Gemini CLI|script dual" "Modo com shell não descrito na skill principal"
assert_contains "$SKILL_FILE" "Fallback sem shell" "Fallback sem shell não descrito na skill principal"
assert_contains "$SKILL_FILE" "prumo_briefing_state\\.py" "Persistência direta: helper script ausente na skill principal"
if [[ -f "$SKILL_MIRROR_FILE" ]]; then
  assert_contains "$SKILL_MIRROR_FILE" "Google dual via Gemini CLI|script dual" "Modo com shell não descrito na skill espelhada"
  assert_contains "$SKILL_MIRROR_FILE" "Fallback sem shell" "Fallback sem shell não descrito na skill espelhada"
fi

assert_contains "$CORE_FILE" "com shell" "Modo com shell não descrito no core"
assert_contains "$CORE_FILE" "sem shell" "Modo sem shell não descrito no core"

STATE_HELPER_FILE="$ROOT_DIR/scripts/prumo_briefing_state.py"
[[ -f "$STATE_HELPER_FILE" ]] || fail "Helper de persistência do briefing ausente"

PUBLIC_VERSION_FILE="$REPO_ROOT/VERSION"
PUBLIC_PLUGIN_FILE="$REPO_ROOT/plugin.json"
PUBLIC_MARKETPLACE_FILE="$REPO_ROOT/marketplace.json"
PUBLIC_PLUGIN_MIRROR_FILE="$REPO_ROOT/.claude-plugin/plugin.json"
PUBLIC_MARKETPLACE_MIRROR_FILE="$REPO_ROOT/.claude-plugin/marketplace.json"
PUBLIC_README_FILE="$REPO_ROOT/README.md"
PUBLIC_CHANGELOG_FILE="$REPO_ROOT/CHANGELOG.md"

for file in "$PUBLIC_VERSION_FILE" "$PUBLIC_PLUGIN_FILE" "$PUBLIC_MARKETPLACE_FILE" "$PUBLIC_PLUGIN_MIRROR_FILE" "$PUBLIC_MARKETPLACE_MIRROR_FILE" "$PUBLIC_README_FILE" "$PUBLIC_CHANGELOG_FILE"; do
  [[ -f "$file" ]] || fail "Arquivo público obrigatório ausente: $file"
done

PUBLIC_VERSION_VALUE="$(cat "$PUBLIC_VERSION_FILE")"
[[ "$PUBLIC_VERSION_VALUE" == "$CORE_VERSION" ]] || fail "Divergência de versão pública: VERSION=$PUBLIC_VERSION_VALUE vs prumo_version=$CORE_VERSION"
[[ "$VERSION_VALUE" == "$CORE_VERSION" ]] || fail "Divergência de versão runtime: cowork-plugin/VERSION=$VERSION_VALUE vs prumo_version=$CORE_VERSION"

assert_contains "$PUBLIC_PLUGIN_FILE" "\"version\": \"$CORE_VERSION\"" "Manifest público do plugin fora de sincronia"
assert_contains "$PUBLIC_MARKETPLACE_FILE" "\"version\": \"$CORE_VERSION\"" "Manifest público do marketplace fora de sincronia"
assert_contains "$PUBLIC_PLUGIN_MIRROR_FILE" "\"version\": \"$CORE_VERSION\"" "Manifest espelho do plugin fora de sincronia"
assert_contains "$PUBLIC_MARKETPLACE_MIRROR_FILE" "\"version\": \"$CORE_VERSION\"" "Manifest espelho do marketplace fora de sincronia"
assert_contains "$PUBLIC_README_FILE" "Versão atual: .*${CORE_VERSION}" "README público fora de sincronia"
assert_contains "$PUBLIC_CHANGELOG_FILE" "^## \\[$CORE_VERSION\\] - " "CHANGELOG público sem entrada da versão atual"

# Regressão: --index-output relativo deve ser path independente de --output
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$TMP_DIR/Inbox4Mobile"
cat > "$TMP_DIR/Inbox4Mobile/item.txt" <<'EOF'
https://example.com/test
EOF

(
  cd "$TMP_DIR"
  python3 "$ROOT_DIR/scripts/generate_inbox_preview.py" \
    --inbox-dir Inbox4Mobile \
    --output Inbox4Mobile/inbox-preview.html \
    --index-output Inbox4Mobile/_preview-index.json >/dev/null
)

[[ -f "$TMP_DIR/Inbox4Mobile/_preview-index.json" ]] || fail "Regressão de path: índice não gerado no local esperado"
[[ ! -f "$TMP_DIR/Inbox4Mobile/Inbox4Mobile/_preview-index.json" ]] || fail "Regressão de path: índice duplicado em Inbox4Mobile/Inbox4Mobile"
assert_contains "$TMP_DIR/Inbox4Mobile/inbox-preview.html" "location\\.protocol === 'file:'" "Regressão YouTube local: fallback para file:// ausente"
assert_contains "$TMP_DIR/Inbox4Mobile/inbox-preview.html" "yt-fallback-caption" "Regressão YouTube local: bloco de fallback ausente"

echo "[OK] Briefing smoke checks passaram."
