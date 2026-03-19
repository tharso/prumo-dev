#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
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

CORE_FILE="cowork-plugin/skills/prumo/references/prumo-core.md"
FORMAT_MODULE="cowork-plugin/skills/prumo/references/modules/interaction-format.md"
BRIEFING_MODULE="cowork-plugin/skills/prumo/references/modules/briefing-procedure.md"
HANDOVER_SKILL="cowork-plugin/skills/handover/SKILL.md"
HIGIENE_MODULE="cowork-plugin/skills/prumo/references/modules/claude-hygiene.md"
DOCTOR_SKILL="cowork-plugin/skills/doctor/SKILL.md"
START_SKILL="cowork-plugin/skills/start/SKILL.md"

for file in "$CORE_FILE" "$FORMAT_MODULE" "$BRIEFING_MODULE" "$HANDOVER_SKILL" "$HIGIENE_MODULE" "$DOCTOR_SKILL" "$START_SKILL"; do
  [[ -f "$file" ]] || fail "Arquivo obrigatório ausente: $file"
done

assert_contains "$CORE_FILE" "Fluxo não perde contagem" "Core não registra regra de numeração contínua"
assert_contains "$CORE_FILE" "Escolha fácil vale ouro" "Core não registra regra de alternativas curtas"
assert_contains "$CORE_FILE" "interaction-format\\.md" "Core não aponta para o módulo de interface"

assert_contains "$FORMAT_MODULE" "Numeração contínua" "Módulo de interface sem regra de numeração"
assert_contains "$FORMAT_MODULE" "Alternativas curtas e respondíveis" "Módulo de interface sem regra de alternativas"
assert_contains "$FORMAT_MODULE" 'não reiniciar do `1\.`' "Módulo de interface sem proibição explícita de reset"

assert_contains "$BRIEFING_MODULE" "numeração contínua" "Briefing não reforça numeração contínua"
assert_contains "$BRIEFING_MODULE" "alternativas respondíveis" "Briefing não reforça alternativas curtas"
assert_contains "$HANDOVER_SKILL" "a\\) listar" "Handover não oferece alternativas curtas"
assert_contains "$HIGIENE_MODULE" "a\\) aplicar só as mudanças seguras" "Higiene não oferece opções de resposta"
assert_contains "$DOCTOR_SKILL" "alternativas curtas" "Doctor não reforça alternativas curtas"
assert_contains "$START_SKILL" "numeração contínua" "Start não reforça continuidade visual"

echo "[OK] Interaction contract smoke checks passaram."
