#!/usr/bin/env bash

set -euo pipefail

MARKETPLACE_NAME="prumo-marketplace"
SESSIONS_ROOT="${HOME}/Library/Application Support/Claude/local-agent-mode-sessions"
REF="main"
OUTPUT_FORMAT="text"
DRY_RUN="0"

usage() {
  cat <<'EOF'
Uso:
  scripts/prumo_cowork_update.sh [--sessions-root PATH] [--marketplace-name NAME] [--ref BRANCH] [--dry-run] [--json]

O que faz:
  1. Localiza os checkouts do marketplace do Prumo usados pelo Cowork
  2. Faz fetch/checkout/pull neles
  3. Atualiza o timestamp em known_marketplaces.json para forçar o app a perceber o refresh
  4. Diz se o plugin instalado ainda ficou atrás da versão anunciada no catálogo

Não tenta editar o cache do plugin instalado na marra.
Produto que remenda store por fora vira relojoeiro de granada.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --sessions-root)
      SESSIONS_ROOT="${2:-}"
      shift 2
      ;;
    --marketplace-name)
      MARKETPLACE_NAME="${2:-}"
      shift 2
      ;;
    --ref)
      REF="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="1"
      shift
      ;;
    --json)
      OUTPUT_FORMAT="json"
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "Dependência ausente: python3" >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "Dependência ausente: git" >&2
  exit 1
fi

python3 - "$SESSIONS_ROOT" "$MARKETPLACE_NAME" "$REF" "$DRY_RUN" "$OUTPUT_FORMAT" <<'PY'
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sessions_root = Path(sys.argv[1]).expanduser()
marketplace_name = sys.argv[2]
ref = sys.argv[3]
dry_run = sys.argv[4] == "1"
output_format = sys.argv[5]


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def run_git(args, cwd: Path, check=True):
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} falhou")
    return completed


def collect_roots(base: Path):
    if not base.exists():
        return []
    roots = []
    for path in base.rglob("cowork_plugins"):
        if path.is_dir() and ((path / "known_marketplaces.json").exists() or (path / "marketplaces").exists()):
            roots.append(path)
    unique = {}
    for root in roots:
        try:
            score = root.stat().st_mtime
        except FileNotFoundError:
            continue
        unique[str(root)] = (root, score)
    return [item[0] for item in sorted(unique.values(), key=lambda entry: entry[1], reverse=True)]


def inspect_plugin_version(root: Path):
    installed_path = root / "installed_plugins.json"
    if not installed_path.exists():
        return None
    data = read_json(installed_path)
    items = data.get("plugins", {}).get("prumo@prumo-marketplace", [])
    if not items:
        return None
    items = sorted(items, key=lambda item: (item.get("lastUpdated", ""), item.get("version", "")), reverse=True)
    return items[0].get("version")


roots = collect_roots(sessions_root)
results = []
timestamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

for root in roots:
    known_path = root / "known_marketplaces.json"
    market_dir = root / "marketplaces" / marketplace_name
    before_head = None
    after_head = None
    before_version = None
    after_version = None
    marketplace_known = False
    plugin_version = inspect_plugin_version(root)
    error = None
    recovered = None

    if known_path.exists():
        known = read_json(known_path)
        marketplace_known = marketplace_name in known
    else:
        known = {}

    if market_dir.exists() and (market_dir / ".git").exists():
        before_head = run_git(["rev-parse", "HEAD"], market_dir).stdout.strip() or None
        version_file = market_dir / "VERSION"
        if version_file.exists():
            before_version = version_file.read_text().strip()

        if not dry_run:
            try:
                run_git(["fetch", "origin", ref], market_dir)
                run_git(["checkout", ref], market_dir)
                try:
                    run_git(["pull", "--ff-only", "origin", ref], market_dir)
                except RuntimeError as ff_exc:
                    # Fast-forward impossível: história do espelho reescrita
                    # (#145 — checkout órfão, sem ancestral comum). O checkout
                    # do marketplace é CACHE de um espelho, não working tree do
                    # usuário — reset pro remoto é a operação semanticamente
                    # correta. Mas só com o checkout LIMPO: nunca resetar por
                    # cima de modificação local.
                    status = run_git(["status", "--porcelain"], market_dir).stdout.strip()
                    if status:
                        raise RuntimeError(
                            "fast-forward impossível E o checkout tem modificações locais — "
                            "não vou resetar por cima delas. Resolva à mão (git status no "
                            f"checkout) e rode de novo. Detalhe: {ff_exc}"
                        )
                    run_git(["reset", "--hard", f"origin/{ref}"], market_dir)
                    recovered = (
                        f"história do espelho divergiu do checkout; checkout limpo "
                        f"resetado para origin/{ref}"
                    )
                if marketplace_known:
                    known[marketplace_name]["lastUpdated"] = timestamp
                    write_json(known_path, known)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)

        after_head = run_git(["rev-parse", "HEAD"], market_dir, check=False).stdout.strip() or None
        if version_file.exists():
            after_version = version_file.read_text().strip()
    else:
        error = "Checkout do marketplace não encontrado neste store."

    results.append(
        {
            "root": str(root),
            "marketplace_known": marketplace_known,
            "marketplace_dir": str(market_dir),
            "before_head": before_head,
            "after_head": after_head,
            "before_version": before_version,
            "after_version": after_version,
            "plugin_version": plugin_version,
            "plugin_reinstall_recommended": bool(plugin_version and after_version and plugin_version != after_version),
            "recovered": recovered,
            "error": error,
        }
    )

payload = {
    "sessions_root": str(sessions_root),
    "marketplace_name": marketplace_name,
    "ref": ref,
    "dry_run": dry_run,
    "roots_updated": len(results),
    "results": results,
}

if output_format == "json":
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    raise SystemExit(0)

print("==> Prumo Cowork update")
print(f"Sessions root: {sessions_root}")
print(f"Marketplace: {marketplace_name}")
print(f"Ref: {ref}")
print(f"Dry-run: {'sim' if dry_run else 'não'}")

if not results:
    print()
    print("Não encontrei nenhum store de plugins do Cowork. Sem store, não há o que atualizar.")
    raise SystemExit(1)

for item in results:
    print()
    print(f"Store: {item['root']}")
    print(f"- checkout: {item['marketplace_dir']}")
    print(f"- versão antes: {item['before_version'] or 'n/d'}")
    print(f"- versão depois: {item['after_version'] or 'n/d'}")
    print(f"- HEAD antes: {(item['before_head'] or 'n/d')[:7] if item['before_head'] else 'n/d'}")
    print(f"- HEAD depois: {(item['after_head'] or 'n/d')[:7] if item['after_head'] else 'n/d'}")
    print(f"- plugin instalado: {item['plugin_version'] or 'n/d'}")
    if item.get("recovered"):
        print(f"- recuperação: {item['recovered']}")
    if item["error"]:
        print(f"- erro: {item['error']}")
    elif item["plugin_reinstall_recommended"]:
        print("- ação: o catálogo foi atualizado, mas o plugin ainda está em outra versão. Reinicie o Cowork e, se precisar, remova só o plugin Prumo e reinstale a partir do marketplace.")
    else:
        print("- ação: marketplace alinhado. Se o app continuar velho, reinicie o Cowork antes de chamar o botão de mentiroso.")
PY
