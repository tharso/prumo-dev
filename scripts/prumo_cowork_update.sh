#!/usr/bin/env bash

set -euo pipefail

MARKETPLACE_NAME="prumo-marketplace"
SESSIONS_ROOT="${HOME}/Library/Application Support/Claude/local-agent-mode-sessions"
PLUGINS_ROOT="${HOME}/.claude/plugins"
REF="main"
OUTPUT_FORMAT="text"
DRY_RUN="0"

usage() {
  cat <<'EOF'
Uso:
  scripts/prumo_cowork_update.sh [--plugins-root PATH] [--sessions-root PATH] [--marketplace-name NAME] [--ref BRANCH] [--dry-run] [--json]

O que faz:
  1. Localiza os checkouts do marketplace do Prumo — a store ATIVA (unificada,
     ~/.claude/plugins) e as LEGADAS (diretórios cowork_plugins nas sessões)
  2. Faz fetch/checkout/pull neles
  3. Atualiza o timestamp em known_marketplaces.json para forçar o app a perceber o refresh
  4. Diz se o plugin instalado ainda ficou atrás da versão anunciada no catálogo

Não tenta editar o cache do plugin instalado na marra.

Cada store aparece no relatório NOMEADA e CLASSIFICADA (ativa ou legada). Se só
houver legada, o script diz isso em voz alta e sai diferente de zero: antes ele
atualizava a legada e reportava "marketplace alinhado", o que fazia quem lia
concluir que o problema tinha sido resolvido (#276).

Escopo (#190): este script alcança só CHECKOUTS GIT LOCAIS (camada 3 da propagação).
O Cowork atual materializa plugins do registro server-side da conta (camada 5) — se a
sessão serve catálogo velho mesmo com checkout em dia, o reparo é outro: remover o
marketplace na UI e re-adicionar como owner/repo (o doctor diagnostica e prescreve).
Produto que remenda store por fora vira relojoeiro de granada.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --sessions-root)
      SESSIONS_ROOT="${2:-}"
      shift 2
      ;;
    --plugins-root)
      PLUGINS_ROOT="${2:-}"
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

python3 - "$SESSIONS_ROOT" "$MARKETPLACE_NAME" "$REF" "$DRY_RUN" "$OUTPUT_FORMAT" "$PLUGINS_ROOT" <<'PY'
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
plugins_root = Path(sys.argv[6]).expanduser() if len(sys.argv) > 6 else None


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


def _e_store(path: Path) -> bool:
    """Marcadores de uma store de plugins, qualquer que seja a topologia."""
    return path.is_dir() and (
        (path / "known_marketplaces.json").exists() or (path / "marketplaces").is_dir()
    )


def collect_roots(sessions_base: Path, plugins_base):
    """Stores ATIVA e LEGADAS, cada uma classificada.

    A versão anterior procurava só por diretórios chamados `cowork_plugins`
    (#276). A store do Cowork atual é `~/.claude/plugins/`, que não tem
    nenhum diretório com esse nome — então ela era estruturalmente invisível,
    e o script atualizava a legada reportando sucesso. O cabeçalho culpava a
    camada, mas a store unificada TAMBÉM é checkout git local: a limitação
    era de padrão de busca.
    """
    achados = []

    if plugins_base is not None and _e_store(plugins_base):
        achados.append((plugins_base, "ativa"))

    if sessions_base.exists():
        for path in sessions_base.rglob("cowork_plugins"):
            if _e_store(path):
                achados.append((path, "legada"))

    unique = {}
    for root, kind in achados:
        chave = str(root)
        if chave in unique:
            continue
        try:
            score = root.stat().st_mtime
        except FileNotFoundError:
            continue
        unique[chave] = (root, kind, score)

    # Ativa primeiro sempre; entre as legadas, a mais recente na frente.
    return [
        (item[0], item[1])
        for item in sorted(
            unique.values(), key=lambda e: (e[1] != "ativa", -e[2])
        )
    ]


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


roots = collect_roots(sessions_root, plugins_root)
results = []
timestamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

for root, kind in roots:
    known_path = root / "known_marketplaces.json"
    market_dir = root / "marketplaces" / marketplace_name
    before_head = None
    after_head = None
    before_version = None
    after_version = None
    marketplace_known = False
    plugin_version = None
    error = None
    recovered = None
    known = {}
    version_file = None

    # A INSPEÇÃO também entra na rede de captura (#276, r23): JSON malformado
    # ou `.git` corrompido estourava ANTES do try e derrubava o script com
    # traceback e rc 1 — sem JSON válido, sem veredito. Contrato de quatro
    # estados que só vale quando nada dá errado não é contrato.
    try:
        plugin_version = inspect_plugin_version(root)
        if known_path.exists():
            known = read_json(known_path)
            marketplace_known = marketplace_name in known
    except Exception as exc:  # noqa: BLE001
        error = f"inspeção do store falhou: {exc}"

    if error is None and market_dir.exists() and (market_dir / ".git").exists():
        try:
            before_head = run_git(["rev-parse", "HEAD"], market_dir).stdout.strip() or None
            version_file = market_dir / "VERSION"
            if version_file.exists():
                before_version = version_file.read_text().strip()
        except Exception as exc:  # noqa: BLE001
            error = f"leitura do checkout falhou: {exc}"

        if not dry_run and error is None:
            try:
                run_git(["fetch", "origin", ref], market_dir)
                run_git(["checkout", ref], market_dir)
                try:
                    run_git(["pull", "--ff-only", "origin", ref], market_dir)
                except RuntimeError as ff_exc:
                    # Fast-forward impossível. O caso CONTRATADO (#145) é o
                    # checkout órfão: história do espelho reescrita, SEM
                    # ancestral comum. Aí o checkout é cache de espelho e o
                    # reset pro remoto é a operação correta. Qualquer outra
                    # causa (modificação local, commits locais) aborta — o
                    # reset destruiria trabalho que não é nosso.
                    status = run_git(["status", "--porcelain"], market_dir).stdout.strip()
                    if status:
                        raise RuntimeError(
                            "fast-forward impossível E o checkout tem modificações locais — "
                            "não vou resetar por cima delas. Resolva à mão (git status no "
                            f"checkout) e rode de novo. Detalhe: {ff_exc}"
                        )
                    merge_base = run_git(
                        ["merge-base", "HEAD", f"origin/{ref}"], market_dir, check=False
                    )
                    if merge_base.returncode == 0 and merge_base.stdout.strip():
                        raise RuntimeError(
                            "fast-forward impossível por COMMITS LOCAIS no checkout "
                            "(há ancestral comum com o remoto) — não vou descartá-los "
                            "com reset. Inspecione com 'git log origin/"
                            f"{ref}..HEAD' no checkout e decida o destino deles. "
                            f"Detalhe: {ff_exc}"
                        )
                    run_git(["reset", "--hard", f"origin/{ref}"], market_dir)
                    recovered = (
                        f"história do espelho divergiu do checkout (sem ancestral "
                        f"comum); checkout limpo resetado para origin/{ref}"
                    )
                if marketplace_known:
                    known[marketplace_name]["lastUpdated"] = timestamp
                    write_json(known_path, known)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)

        if error is None:
            after_head = run_git(["rev-parse", "HEAD"], market_dir, check=False).stdout.strip() or None
            if version_file is not None and version_file.exists():
                after_version = version_file.read_text().strip()
    elif error is None:
        error = "Checkout do marketplace não encontrado neste store."

    results.append(
        {
            "root": str(root),
            "kind": kind,
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

ativas = [item for item in results if item["kind"] == "ativa"]
tem_ativa = bool(ativas)
tem_legada = any(item["kind"] == "legada" for item in results)
# ACHAR não é ATUALIZAR: store ativa com checkout ausente ou git que falhou
# saía com sucesso, que é exatamente a mentira que esta issue remove.
# `error is None` num dry-run significa "nada deu errado porque nada foi
# tentado". Sem esta distinção o dry-run ganhava diploma por não comparecer
# à aula: `active_store_updated: true`, `stores_updated: 1`, status `ok`
# (Codex, r23).
ativa_sem_erro = tem_ativa and all(item["error"] is None for item in ativas)
ativa_ok = ativa_sem_erro and not dry_run

REPARO_CAMADA5 = (
    "se o catálogo continuar velho com a store ativa em dia, o reparo é da "
    "camada 5: remover o marketplace na UI e re-adicionar como owner/repo"
)

if not results:
    estado, codigo = "sem_store", 1
    veredito = "nenhum store de plugins encontrado — não há o que atualizar"
elif dry_run:
    estado, codigo = ("simulacao", 0) if ativa_sem_erro else ("ativa_falhou", 4)
    veredito = (
        "SIMULAÇÃO: nada foi escrito. "
        + (
            "a store ATIVA está acessível e seria atualizável"
            if ativa_sem_erro
            else "a store ATIVA não está em condição de ser atualizada"
        )
    )
elif not tem_ativa:
    estado, codigo = "so_legada", 3
    veredito = (
        "a store ATIVA (unificada) não foi encontrada; só atualizei store "
        f"LEGADA, o que não muda o que o Cowork carrega. {REPARO_CAMADA5}"
    )
elif not ativa_ok:
    estado, codigo = "ativa_falhou", 4
    veredito = "a store ATIVA foi encontrada mas NÃO foi atualizada: " + "; ".join(
        item["error"] for item in ativas if item["error"]
    )
else:
    estado, codigo = "ok", 0
    veredito = f"store ATIVA atualizada. {REPARO_CAMADA5}"

payload = {
    "sessions_root": str(sessions_root),
    "plugins_root": str(plugins_root) if plugins_root else None,
    "marketplace_name": marketplace_name,
    "ref": ref,
    "dry_run": dry_run,
    "stores_found": len(results),
    "stores_updated": 0 if dry_run else sum(1 for item in results if item["error"] is None),
    "active_store_reached": tem_ativa,
    "active_store_updated": ativa_ok,
    "status": estado,
    "verdict": veredito,
    "results": results,
}

if output_format == "json":
    # Um estado só, calculado acima: texto e JSON não podem discordar sobre
    # o que aconteceu nem sobre o código de saída (#276).
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    raise SystemExit(codigo)

print("==> Prumo Cowork update")
print(f"Store ativa (procurada em): {plugins_root or 'n/d'}")
print(f"Sessions root (legadas): {sessions_root}")
print(f"Marketplace: {marketplace_name}")
print(f"Ref: {ref}")
print(f"Dry-run: {'sim' if dry_run else 'não'}")

if not results:
    print()
    print("Não encontrei nenhum store de plugins do Cowork. Sem store, não há o que atualizar.")
    raise SystemExit(codigo)

for item in results:
    print()
    rotulo = "ATIVA (unificada)" if item["kind"] == "ativa" else "LEGADA (cowork_plugins)"
    print(f"Store [{rotulo}]: {item['root']}")
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
    elif item["kind"] == "ativa":
        print("- ação: marketplace alinhado NA STORE ATIVA. Se o app continuar velho, reinicie o Cowork antes de chamar o botão de mentiroso.")
    else:
        print("- ação: store legada alinhada — e isso NÃO resolve o Cowork atual. Ela é entulho de arranjo antigo (≤março/2026).")

print()
print(f"Veredito: {veredito}")
if estado == "so_legada":
    print(f"Procurei a store ativa em: {plugins_root or 'n/d'}")
    print("Se o caminho for outro nesta máquina, passe --plugins-root.")
elif estado == "ativa_falhou":
    print("A store que decide o comportamento NÃO está em dia.")
raise SystemExit(codigo)
PY
