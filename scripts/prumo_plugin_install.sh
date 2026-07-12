#!/usr/bin/env bash

set -euo pipefail

MARKETPLACE_NAME="prumo-marketplace"
PLUGIN_NAME="prumo@prumo-marketplace"
MARKETPLACE_SOURCE="https://github.com/tharso/prumo.git"
SCOPE="user"
FORCE_READD="0"

usage() {
  cat <<'EOF'
Uso:
  scripts/prumo_plugin_install.sh [--scope user|project|local] [--marketplace-source SOURCE] [--marketplace-url SOURCE] [--force-readd]

O que faz:
  1. Garante que o marketplace do Prumo existe no backend do Claude
  2. Atualiza ou adiciona o marketplace pelo CLI
  3. Instala ou atualiza o plugin prumo nesse backend

Observação importante:
  Este script não corrige sozinho o store local do Cowork quando a UI congela o catálogo.
  Para isso, use:
    - scripts/prumo_cowork_doctor.sh
    - scripts/prumo_cowork_update.sh

Exemplos:
  scripts/prumo_plugin_install.sh
  scripts/prumo_plugin_install.sh --scope user
  scripts/prumo_plugin_install.sh --marketplace-source https://github.com/tharso/prumo.git --force-readd
  scripts/prumo_plugin_install.sh --marketplace-url https://raw.githubusercontent.com/tharso/prumo/<commit>/marketplace.json --force-readd
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope)
      SCOPE="${2:-}"
      shift 2
      ;;
    --marketplace-source|--marketplace-url)
      MARKETPLACE_SOURCE="${2:-}"
      shift 2
      ;;
    --force-readd)
      FORCE_READD="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Argumento desconhecido: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Dependência ausente: $1" >&2
    exit 1
  fi
}

need_cmd claude
need_cmd python3

has_marketplace() {
  claude plugin marketplace list --json | python3 -c 'import json, sys; name = sys.argv[1]; items = json.load(sys.stdin); print("yes" if any(item.get("name") == name for item in items) else "no")' "$MARKETPLACE_NAME"
}

has_plugin() {
  claude plugin list --json | python3 -c 'import json, sys; plugin_id = sys.argv[1]; items = json.load(sys.stdin); print("yes" if any(item.get("id") == plugin_id for item in items) else "no")' "$PLUGIN_NAME"
}

echo "==> Prumo plugin installer"
echo "Marketplace: $MARKETPLACE_NAME"
echo "Plugin: $PLUGIN_NAME"
echo "Scope: $SCOPE"
echo "Source: $MARKETPLACE_SOURCE"

if [ "$FORCE_READD" = "1" ] && [ "$(has_marketplace)" = "yes" ]; then
  echo "==> Removendo marketplace antigo para forçar recadastro"
  claude plugin marketplace remove "$MARKETPLACE_NAME"
fi

if [ "$(has_marketplace)" = "yes" ]; then
  echo "==> Atualizando marketplace existente"
  claude plugin marketplace update "$MARKETPLACE_NAME"
else
  echo "==> Adicionando marketplace"
  claude plugin marketplace add "$MARKETPLACE_SOURCE"
fi

if [ "$(has_plugin)" = "yes" ]; then
  echo "==> Atualizando plugin instalado"
  claude plugin update --scope "$SCOPE" "$PLUGIN_NAME"
else
  echo "==> Instalando plugin"
  claude plugin install --scope "$SCOPE" "$PLUGIN_NAME"
fi

echo
echo "Prumo instalado/atualizado com sucesso."
echo "Próximos passos:"
echo "1. Feche totalmente o Cowork/Claude Desktop."
echo "2. Abra o app de novo."
echo "3. Abra uma conversa nova."
echo "4. Teste /setup, /briefing ou /higiene — ou peça \"diagnostica o runtime\" (doctor)."
echo
echo "Se o Cowork continuar preso em catálogo velho com botão apagado, não negocie com a UI:"
echo "  - scripts/prumo_cowork_doctor.sh"
echo "  - scripts/prumo_cowork_update.sh"
