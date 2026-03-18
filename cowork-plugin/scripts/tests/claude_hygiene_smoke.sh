#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

assert_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if command -v rg >/dev/null 2>&1; then
    rg -q -- "$pattern" "$file" || fail "$label (arquivo: $file)"
    return 0
  fi
  grep -Eq -- "$pattern" "$file" || fail "$label (arquivo: $file)"
}

assert_not_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if command -v rg >/dev/null 2>&1; then
    rg -q -- "$pattern" "$file" && fail "$label (arquivo: $file)"
    return 0
  fi
  grep -Eq -- "$pattern" "$file" && fail "$label (arquivo: $file)"
}

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$TMP_DIR/_state" "$TMP_DIR/_backup"

cat > "$TMP_DIR/CLAUDE.md" <<'EOF'
# CLAUDE

Quero texto direto, sem rodeios.

Evite emojis.

Evite emojis.

Prefira não usar travessão.

Pode usar travessão se soar melhor.

## Rotina

Cobrar itens parados com humor seco.

Cobrar itens parados com humor seco.

## Lembretes

- Checar contrato em 01/01/2026.

## Infra

- Domínios transferindo desde 01/01/2026.
- Serviço migrando desde 02/01/2026.

## Changelog

- **05/02/2026**: Sistema criado como Claudia.
- **06/02/2026**: Migração para Prumo.

## Perfil

- Conheci Mari em 01/01/2016.
EOF

cat > "$TMP_DIR/REGISTRO.md" <<'EOF'
# Registro

| Data | Origem | Resumo | Ação | Destino |
|------|--------|--------|------|---------|
EOF

python3 "$ROOT_DIR/scripts/prumo_claude_hygiene.py" --workspace "$TMP_DIR" >/dev/null

[[ -f "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.json" ]] || fail "Relatorio JSON ausente"
[[ -f "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" ]] || fail "Relatorio MD ausente"
[[ -f "$TMP_DIR/_state/claude-hygiene/claude-hygiene.patch" ]] || fail "Patch proposto ausente"
[[ -f "$TMP_DIR/_state/claude-hygiene/CLAUDE.proposed.md" ]] || fail "CLAUDE proposto ausente"
assert_contains "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" "Duplicado" "Relatorio nao apontou duplicacao"
assert_contains "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" "Potencial conflito" "Relatorio nao apontou conflito"
assert_contains "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" "Lembrete vencido no arquivo vivo" "Relatorio nao apontou lembrete vencido"
assert_contains "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" "Histórico no arquivo vivo" "Relatorio nao apontou historico deslocado"
assert_contains "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" "Status transitório envelhecido" "Relatorio nao apontou status transitorio envelhecido"
assert_contains "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" "PAUTA.md / REGISTRO.md" "Relatorio nao sugeriu destino para lembrete vencido"
assert_contains "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" "REGISTRO.md / CHANGELOG" "Relatorio nao sugeriu destino para historico"
assert_not_contains "$TMP_DIR/_state/claude-hygiene/claude-hygiene-report.md" "Conheci Mari em 01/01/2016" "Relatorio gerou falso positivo no caso negativo"
assert_contains "$TMP_DIR/CLAUDE.md" "Evite emojis." "Dry-run alterou CLAUDE.md"

python3 "$ROOT_DIR/scripts/prumo_claude_hygiene.py" --workspace "$TMP_DIR" --apply >/dev/null

[[ -f "$(find "$TMP_DIR/_backup" -maxdepth 1 -type f -name 'CLAUDE.md.*' | head -n1)" ]] || fail "Backup do CLAUDE nao foi criado"
assert_contains "$TMP_DIR/REGISTRO.md" "Higiene assistida aplicada ao CLAUDE.md" "REGISTRO nao foi atualizado"

EMOJI_COUNT="$(grep -c "^Evite emojis\.$" "$TMP_DIR/CLAUDE.md")"
[[ "$EMOJI_COUNT" -eq 1 ]] || fail "Aplicacao nao removeu duplicacao literal"
assert_contains "$TMP_DIR/CLAUDE.md" "Checar contrato em 01/01/2026" "Aplicacao removeu item que exigia confirmacao factual"

echo "[OK] Claude hygiene smoke checks passaram."
