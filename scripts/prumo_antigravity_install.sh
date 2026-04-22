#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=""
SCOPE="global"
WORKSPACE_DIR="$(pwd)"
TEMP_SOURCE_DIR=""
ARCHIVE_URL="${PRUMO_INSTALL_ARCHIVE_URL:-https://github.com/tharso/prumo/archive/refs/heads/main.tar.gz}"

usage() {
  cat <<'EOF'
Uso: prumo_antigravity_install.sh [opções]

Instala as skills do Prumo no formato que o Google Antigravity enxerga.

Opções:
  --scope global       Instala em ~/.gemini/antigravity/skills/ (default)
  --scope workspace    Instala em <workspace>/.agent/skills/
  --workspace <dir>    Usado junto com --scope workspace. Default: diretório atual.
  -h, --help           Mostra esta mensagem.

Variáveis de ambiente:
  PRUMO_INSTALL_ROOT_DIR  Caminho para o checkout do repo (opcional).
  PRUMO_INSTALL_ARCHIVE_URL  Override do snapshot baixado quando não há repo local.
EOF
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "erro: dependência ausente: $1" >&2
    exit 1
  fi
}

cleanup() {
  if [ -n "$TEMP_SOURCE_DIR" ] && [ -d "$TEMP_SOURCE_DIR" ]; then
    rm -rf "$TEMP_SOURCE_DIR"
  fi
}

trap cleanup EXIT

while [ $# -gt 0 ]; do
  case "$1" in
    --scope)
      SCOPE="${2:-}"
      shift 2
      ;;
    --workspace)
      WORKSPACE_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "erro: argumento desconhecido: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$SCOPE" in
  global|workspace) ;;
  *)
    echo "erro: --scope deve ser 'global' ou 'workspace' (recebi: $SCOPE)" >&2
    exit 1
    ;;
esac

bootstrap_source_archive() {
  need_cmd curl
  need_cmd tar
  TEMP_SOURCE_DIR="$(mktemp -d)"
  local archive_path="$TEMP_SOURCE_DIR/prumo.tar.gz"
  echo "Repo local não encontrado. Baixando snapshot para copiar as skills."
  echo "Archive: $ARCHIVE_URL"
  curl -fsSL --proto =https --tlsv1.2 "$ARCHIVE_URL" -o "$archive_path"
  tar -xzf "$archive_path" -C "$TEMP_SOURCE_DIR"
  ROOT_DIR="$(find "$TEMP_SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d -name 'prumo-*' | head -n 1)"
  if [ -z "$ROOT_DIR" ] || [ ! -d "$ROOT_DIR/skills" ]; then
    echo "erro: snapshot baixado não tem skills/." >&2
    exit 1
  fi
}

resolve_root_dir() {
  if [ -n "${PRUMO_INSTALL_ROOT_DIR:-}" ] && [ -d "${PRUMO_INSTALL_ROOT_DIR}/skills" ]; then
    ROOT_DIR="$(cd "${PRUMO_INSTALL_ROOT_DIR}" && pwd)"
    return 0
  fi

  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local candidate_root
  candidate_root="$(cd "${script_dir}/.." && pwd)"

  if [ -d "${candidate_root}/skills" ] && [ -f "${candidate_root}/VERSION" ]; then
    ROOT_DIR="$candidate_root"
    return 0
  fi

  bootstrap_source_archive
}

resolve_root_dir

if [ "$SCOPE" = "global" ]; then
  TARGET_DIR="$HOME/.gemini/antigravity/skills"
else
  if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "erro: workspace não existe: $WORKSPACE_DIR" >&2
    exit 1
  fi
  TARGET_DIR="$(cd "$WORKSPACE_DIR" && pwd)/.agent/skills"
fi

VERSION="$(cat "$ROOT_DIR/VERSION" 2>/dev/null || echo 'desconhecida')"

echo "==> Instalando skills do Prumo para o Antigravity"
echo "Repo: $ROOT_DIR"
echo "Versão: $VERSION"
echo "Escopo: $SCOPE"
echo "Destino: $TARGET_DIR"

mkdir -p "$TARGET_DIR"

copy_skills() {
  local src="$ROOT_DIR/skills"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --exclude '__pycache__' \
      --exclude '.DS_Store' \
      "$src"/ "$TARGET_DIR"/
  else
    # fallback sem rsync: remove destino das skills conhecidas e recopia
    local skill
    for skill in "$src"/*/; do
      [ -d "$skill" ] || continue
      local name
      name="$(basename "$skill")"
      rm -rf "$TARGET_DIR/$name"
      cp -R "$skill" "$TARGET_DIR/$name"
    done
    find "$TARGET_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
    find "$TARGET_DIR" -name '.DS_Store' -delete
  fi
}

copy_skills

echo ""
echo "Skills instaladas. Listagem:"
ls -1 "$TARGET_DIR" | sed 's/^/  - /'

echo ""
echo "Teste rápido no Antigravity:"
echo "1. Abra o Antigravity e crie um agente."
if [ "$SCOPE" = "global" ]; then
  echo "2. A skill 'prumo' fica disponível em qualquer workspace."
else
  echo "2. Abra o workspace ($WORKSPACE_DIR). As skills ficam escopadas a ele."
fi
echo "3. Peça ao agente: 'Use a skill prumo e me guie pelo setup.'"
