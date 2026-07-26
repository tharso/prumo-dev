#!/usr/bin/env bash

set -euo pipefail

MARKETPLACE_NAME="prumo-marketplace"
PLUGIN_ID="prumo@prumo-marketplace"
SESSIONS_ROOT="${HOME}/Library/Application Support/Claude/local-agent-mode-sessions"
OUTPUT_FORMAT="text"
# Stores globais (#146): o plugin INSTALADO do Cowork mora em
# ~/.claude/cowork_plugins e o do Claude Code CLI em ~/.claude/plugins.
# Só varrer o sessions-root dava falso-negativo ("nada urgente") enquanto
# um plugin de era antiga apodrecia no store global. Array (não string com
# separador) pra path com ':' não quebrar o parse.
EXTRA_ROOTS=("${HOME}/.claude/cowork_plugins" "${HOME}/.claude/plugins" "${HOME}/.codex/plugins")
EXTRA_ROOTS_OVERRIDDEN=0
WORKSPACE_PATH=""
OFFLINE_FLAG="0"

usage() {
  cat <<'EOF'
Uso:
  scripts/prumo_cowork_doctor.sh [--sessions-root PATH] [--extra-root PATH]... [--marketplace-name NAME] [--plugin-id ID] [--workspace PATH] [--offline] [--json]

O que faz:
  1. Localiza os stores reais de plugins (sessões do Cowork + ~/.claude/cowork_plugins + ~/.claude/plugins + ~/.codex/plugins)
  2. Inspeciona o checkout do marketplace usado pelo Cowork
  3. Compara versão do plugin instalado, versão do checkout local e HEAD remoto do repositório
  4. Flagra plugin de era antiga (pré-5.x) e catálogo fresco com instalação defasada
  5. Com --workspace: drift plugin↔workspace (prumo_version do core vs plugin instalado) (#179 PR9)
  6. Enumera caches de plugin (cache/<mkt>/<plugin>/<versão>) com bytes e comando de remoção PRONTO — nunca executa
  7. Hash agregado das árvores de skills (checkout vs instalado) — drift de conteúdo com versões iguais

Nota: --extra-root é repetível e SUBSTITUI os defaults na primeira ocorrência.
      --offline pula TODA rede (ls-remote e staleness por URL) — pra diagnóstico hermético.

Exemplos:
  scripts/prumo_cowork_doctor.sh
  scripts/prumo_cowork_doctor.sh --json --workspace ~/Documents/DailyLife
  scripts/prumo_cowork_doctor.sh --sessions-root "/tmp/fake-cowork" --extra-root "/tmp/fake-store" --offline
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --sessions-root)
      SESSIONS_ROOT="${2:-}"
      shift 2
      ;;
    --extra-root)
      if [ "$EXTRA_ROOTS_OVERRIDDEN" -eq 0 ]; then
        EXTRA_ROOTS=()
        EXTRA_ROOTS_OVERRIDDEN=1
      fi
      EXTRA_ROOTS+=("${2:-}")
      shift 2
      ;;
    --marketplace-name)
      MARKETPLACE_NAME="${2:-}"
      shift 2
      ;;
    --plugin-id)
      PLUGIN_ID="${2:-}"
      shift 2
      ;;
    --workspace)
      WORKSPACE_PATH="${2:-}"
      shift 2
      ;;
    --offline)
      OFFLINE_FLAG="1"
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

export PRUMO_COWORK_DOCTOR_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

python3 - "$SESSIONS_ROOT" "$MARKETPLACE_NAME" "$PLUGIN_ID" "$OUTPUT_FORMAT" "$WORKSPACE_PATH" "$OFFLINE_FLAG" "${EXTRA_ROOTS[@]}" <<'PY'
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sessions_root = Path(sys.argv[1]).expanduser()
marketplace_name = sys.argv[2]
plugin_id = sys.argv[3]
output_format = sys.argv[4]
workspace_arg = sys.argv[5]
offline = sys.argv[6] == "1"
extra_roots = [Path(p).expanduser() for p in sys.argv[7:] if p]
script_dir = Path(os.environ["PRUMO_COWORK_DOCTOR_SCRIPT_DIR"])
repo_root = script_dir.parent
plugin_name = plugin_id.split("@", 1)[0]


def read_json(path: Path):
    return json.loads(path.read_text())


def read_text(path: Path):
    return path.read_text().strip()


def run_git(args, cwd: Path):
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return completed.stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        # OSError cobre FileNotFoundError e NotADirectoryError — visto na
        # máquina real: marketplaces/<nome> pode ser um ARQUIVO (#146).
        return None


def semver_tuple(value):
    if not value:
        return ()
    parts = []
    for chunk in str(value).split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            return ()
    return tuple(parts)


def fetch_url_version(url: str, timeout: float = 1.5):
    # Staleness pra marketplace com source "url" (#179 PR9): busca o VERSION
    # publicado ao lado do manifesto, com timeout curto — doctor não pode
    # pendurar num DNS morto. Qualquer falha → None (sem rede não é erro).
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read(256).decode("utf-8", errors="replace").strip() or None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def read_workspace_core_version(workspace: Path):
    core = workspace / ".prumo" / "system" / "PRUMO-CORE.md"
    try:
        head = core.read_text(errors="replace")[:2000]
    except OSError:
        return None
    match = re.search(r"prumo_version:\s*([0-9]+(?:\.[0-9]+)*)", head)
    return match.group(1) if match else None


def tree_hash(base: Path):
    # Hash agregado de uma árvore de skills: caminho relativo + conteúdo,
    # em ordem estável. Detecta drift de CONTEÚDO mesmo com versões iguais
    # (checkout editado à mão, instalação corrompida). Symlinks ficam fora —
    # mesma postura do sanitize (#179).
    if not base.is_dir():
        return None
    digest = hashlib.sha256()
    try:
        for item in sorted(base.rglob("*"), key=lambda p: p.relative_to(base).as_posix()):
            if item.is_symlink() or not item.is_file():
                continue
            digest.update(item.relative_to(base).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(item.read_bytes())
            digest.update(b"\0")
    except OSError:
        return None
    return digest.hexdigest()


def dir_size_bytes(base: Path):
    total = 0
    try:
        for item in base.rglob("*"):
            if not item.is_symlink() and item.is_file():
                total += item.stat().st_size
    except OSError:
        pass
    return total


def enumerate_caches(bases, protected_paths, protected_versions):
    # Enumera cache/<mkt>/<plugin>/<versão> nos stores (#179 PR9). Só REPORTA
    # e monta o comando de remoção pronto pra colar — nunca remove nada.
    caches = []
    seen = set()
    for base in bases:
        cache_dir = base / "cache" / marketplace_name / plugin_name
        if not cache_dir.is_dir():
            continue
        for vdir in sorted(cache_dir.iterdir()):
            if not vdir.is_dir() or vdir.is_symlink():
                continue
            key = str(vdir.resolve())
            if key in seen:
                continue
            seen.add(key)
            in_use = key in protected_paths or vdir.name in protected_versions
            entry = {
                "root": str(base),
                "path": str(vdir),
                "version": vdir.name,
                "bytes": dir_size_bytes(vdir),
                "status": "em_uso" if in_use else "stale",
                "remove_command": None if in_use else f"rm -rf {shlex.quote(str(vdir))}",
            }
            caches.append(entry)
    return caches


def collect_roots(base: Path, extras: list):
    roots = []
    if base.exists():
        for path in base.rglob("cowork_plugins"):
            if not path.is_dir():
                continue
            if (path / "known_marketplaces.json").exists() or (path / "installed_plugins.json").exists():
                roots.append(path)

    # Stores globais (#146): onde o plugin INSTALADO realmente mora.
    for extra in extras:
        if not extra.is_dir():
            continue
        if (extra / "known_marketplaces.json").exists() or (extra / "installed_plugins.json").exists():
            roots.append(extra)

    unique = {}
    for root in roots:
        try:
            score = root.stat().st_mtime
        except FileNotFoundError:
            continue
        unique[str(root)] = (root, score)

    return [item[0] for item in sorted(unique.values(), key=lambda entry: entry[1], reverse=True)]


def inspect_root(root: Path):
    known_path = root / "known_marketplaces.json"
    installed_path = root / "installed_plugins.json"

    known = read_json(known_path) if known_path.exists() else {}
    installed = read_json(installed_path) if installed_path.exists() else {"plugins": {}}

    marketplace_entry = known.get(marketplace_name)
    install_location = None
    source = None
    last_updated = None
    if marketplace_entry:
        loc = marketplace_entry.get("installLocation")
        # Path("") é o CWD (e CWD é diretório) — entrada sem installLocation
        # faria o doctor inspecionar silenciosamente o diretório errado (#145).
        install_location = Path(loc) if loc else None
        source = marketplace_entry.get("source", {})
        last_updated = marketplace_entry.get("lastUpdated")
    if install_location is None:
        fallback = root / "marketplaces" / marketplace_name
        if fallback.exists():
            install_location = fallback

    checkout_version = None
    checkout_declared_version = None
    checkout_head = None
    checkout_branch = None
    remote_head = None
    remote_version_url = None
    checkout_stale = None
    checkout_divergence = None

    if install_location and install_location.is_dir():
        version_file = install_location / "VERSION"
        market_file = install_location / "marketplace.json"

        if version_file.exists():
            checkout_version = read_text(version_file)
        if market_file.exists():
            try:
                data = read_json(market_file)
                for plugin in data.get("plugins", []):
                    if plugin.get("name") == plugin_id.split("@", 1)[0]:
                        checkout_declared_version = plugin.get("version")
                        break
            except json.JSONDecodeError:
                pass

        checkout_head = run_git(["rev-parse", "HEAD"], install_location)
        checkout_branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], install_location)

        if source and source.get("source") in {"git", "github"} and not offline:
            if source["source"] == "git":
                remote_url = source.get("url")
            else:
                remote_url = f"https://github.com/{source.get('repo')}.git"
            ref = "main"
            remote_head = run_git(["ls-remote", remote_url, f"refs/heads/{ref}"], install_location)
            if remote_head:
                remote_head = remote_head.split()[0]
        elif source and source.get("source") == "url" and not offline:
            # Marketplace por URL não tem git — staleness compara o VERSION
            # publicado ao lado do manifesto com o VERSION do checkout.
            src_url = source.get("url") or ""
            if src_url:
                base_url = src_url.rsplit("/", 1)[0] if src_url.endswith(".json") else src_url.rstrip("/")
                remote_version_url = fetch_url_version(f"{base_url}/VERSION")
            if remote_version_url and checkout_version:
                checkout_stale = remote_version_url != checkout_version
        if checkout_head and remote_head:
            checkout_stale = checkout_head != remote_head
        if checkout_stale and remote_head:
            # Classificar sem mutar o cache: só dá pra saber a natureza quando
            # o objeto remoto já existe localmente (fetch anterior). Sem ele,
            # fica indeterminado — o update resolve com segurança em qualquer
            # caso (#145). Três naturezas:
            #   atras          → HEAD é ancestral do remoto (ff possível)
            #   commits_locais → ancestral comum existe, mas há commits locais
            #   divergente     → sem ancestral comum (história reescrita)
            has_remote_obj = run_git(["cat-file", "-e", remote_head], install_location)
            if has_remote_obj is not None:
                is_ancestor = run_git(
                    ["merge-base", "--is-ancestor", checkout_head, remote_head],
                    install_location,
                )
                if is_ancestor is not None:
                    checkout_divergence = "atras"
                else:
                    merge_base = run_git(["merge-base", checkout_head, remote_head], install_location)
                    checkout_divergence = "commits_locais" if merge_base else "divergente"

    installed_items = installed.get("plugins", {}).get(plugin_id, [])
    installed_item = None
    if installed_items:
        installed_item = sorted(
            installed_items,
            key=lambda item: (item.get("lastUpdated", ""), item.get("installedAt", ""), item.get("version", "")),
            reverse=True,
        )[0]

    installed_version = installed_item.get("version") if installed_item else None
    installed_commit = installed_item.get("gitCommitSha") if installed_item else None
    install_path = installed_item.get("installPath") if installed_item else None

    # Caches "em uso" (#179 PR9): TODO installPath listado protege o cache
    # correspondente — não só o item mais novo. Remover cache referenciado
    # por uma entrada instalada quebra a instalação.
    all_install_paths = []
    all_installed_versions = []
    for item in installed_items:
        path_value = item.get("installPath")
        if path_value:
            all_install_paths.append(str(Path(path_value).expanduser().resolve()))
        if item.get("version"):
            all_installed_versions.append(item["version"])

    # Drift de conteúdo (#179 PR9): hash agregado das árvores de skills.
    # Interessante quando as VERSÕES batem mas o conteúdo não (checkout
    # editado à mão, instalação corrompida) — versão diferente já é drift
    # trivial e não precisa de hash pra aparecer.
    checkout_skills_hash = None
    installed_skills_hash = None
    skills_content_drift = None
    if install_location and install_location.is_dir():
        checkout_skills_hash = tree_hash(install_location / "skills")
    if install_path:
        installed_skills_hash = tree_hash(Path(install_path).expanduser() / "skills")
    if checkout_skills_hash and installed_skills_hash and installed_version and checkout_version:
        if installed_version == checkout_version:
            skills_content_drift = checkout_skills_hash != installed_skills_hash

    local_market_version = checkout_declared_version or checkout_version
    plugin_update_recommended = False
    if installed_version and local_market_version:
        plugin_update_recommended = semver_tuple(installed_version) < semver_tuple(local_market_version)

    notes = []
    actions = []

    if not marketplace_entry:
        notes.append("Marketplace não encontrado neste store do Cowork.")
        actions.append("Adicione o marketplace prumo-marketplace no Cowork antes de diagnosticar update.")
    elif not install_location or not install_location.is_dir():
        notes.append("O marketplace está registrado, mas o checkout local não existe mais (ou virou arquivo).")
        actions.append("Remova e adicione o marketplace novamente no Cowork.")
    else:
        if checkout_stale:
            if checkout_divergence == "divergente":
                notes.append("O checkout local do marketplace DIVERGIU do remoto — sem ancestral comum (história do espelho reescrita). Fast-forward nunca vai funcionar aqui (#145).")
                actions.append("Rode scripts/prumo_cowork_update.sh — ele detecta a divergência e reseta o checkout limpo para o remoto.")
            elif checkout_divergence == "commits_locais":
                notes.append("O checkout do marketplace tem COMMITS LOCAIS que o remoto não tem — fast-forward impossível, e o update NÃO vai resetar por cima deles. Estado anômalo para um cache de espelho.")
                actions.append("Inspecione o checkout à mão (git log origin/main..HEAD) e decida o destino dos commits antes de atualizar.")
            else:
                notes.append("O checkout local do marketplace está defasado em relação ao HEAD remoto.")
                actions.append("Rode scripts/prumo_cowork_update.sh para atualizar o checkout do marketplace do Cowork.")

        if installed_version and local_market_version and semver_tuple(installed_version) > semver_tuple(local_market_version):
            notes.append("O plugin instalado está mais novo que o catálogo local. Isso costuma deixar o botão Atualizar apagado por motivo errado.")
            actions.append("Atualize primeiro o checkout do marketplace. Depois reinicie o Cowork.")

        if plugin_update_recommended:
            notes.append("O plugin instalado está atrás da versão anunciada pelo marketplace local.")
            actions.append("Depois de atualizar o marketplace, remova só o plugin Prumo e reinstale pelo Cowork se o botão ainda não acordar.")

        if skills_content_drift:
            notes.append(
                "As skills instaladas DIFEREM do checkout do marketplace apesar da versão ser a mesma "
                f"({installed_version}) — conteúdo editado à mão ou instalação corrompida."
            )
            actions.append("Remova o plugin Prumo e reinstale pelo marketplace pra realinhar o conteúdo.")

    # Era pré-skills-first (#146): plugin < 5.x tem a estrutura antiga
    # (cowork-plugin/), sem as skills atuais — invocar qualquer comando novo
    # dá "Habilidade desconhecida".
    if installed_version and semver_tuple(installed_version) and semver_tuple(installed_version) < (5,):
        notes.append(
            f"O plugin instalado ({installed_version}) é da era pré-skills-first (< 5.x, estrutura antiga). "
            "Skills atuais (fim, acervo, menu...) não existem nele — é disso que nasce 'Habilidade desconhecida'."
        )
        actions.append(
            "Remova o plugin Prumo no host e reinstale pelo marketplace atualizado; depois reinicie o app."
        )

    expected_repo_version = None
    version_file = repo_root / "VERSION"
    if version_file.exists():
        expected_repo_version = read_text(version_file)

    return {
        "root": str(root),
        "marketplace_known": bool(marketplace_entry),
        "marketplace_source": source,
        "marketplace_last_updated": last_updated,
        "marketplace_checkout_path": str(install_location) if install_location else None,
        "marketplace_checkout_branch": checkout_branch,
        "marketplace_checkout_head": checkout_head,
        "marketplace_checkout_version": checkout_version,
        "marketplace_declared_plugin_version": checkout_declared_version,
        "marketplace_remote_head": remote_head,
        "marketplace_remote_version_url": remote_version_url,
        "marketplace_checkout_stale": checkout_stale,
        "marketplace_checkout_divergence": checkout_divergence,
        "plugin_installed": bool(installed_item),
        "plugin_version": installed_version,
        "plugin_git_commit": installed_commit,
        "plugin_install_path": install_path,
        "plugin_update_recommended": plugin_update_recommended,
        "checkout_skills_hash": checkout_skills_hash,
        "installed_skills_hash": installed_skills_hash,
        "skills_content_drift": skills_content_drift,
        "all_install_paths": all_install_paths,
        "all_installed_versions": all_installed_versions,
        "expected_repo_version": expected_repo_version,
        "diagnosis": notes,
        "recommended_actions": actions,
    }


roots = collect_roots(sessions_root, extra_roots)
inspections = [inspect_root(root) for root in roots]

# Caches (#179 PR9): varridos sobre TODOS os candidatos (roots com manifest +
# extras crus) — cache órfão costuma viver justamente em store sem manifest.
cache_bases = []
cache_seen = set()
for candidate in [*roots, *extra_roots]:
    if not candidate.is_dir():
        continue
    key = str(candidate.resolve())
    if key in cache_seen:
        continue
    cache_seen.add(key)
    cache_bases.append(candidate)
protected_paths = set()
protected_versions = set()
for inspection in inspections:
    protected_paths.update(inspection["all_install_paths"])
    protected_versions.update(inspection["all_installed_versions"])
caches = enumerate_caches(cache_bases, protected_paths, protected_versions)
stale_caches = [c for c in caches if c["status"] == "stale"]
# Target = o store onde o plugin está INSTALADO (é lá que a invocação resolve).
# Empate entre stores instalados: preferir o do COWORK (cowork_plugins) — este
# doctor diagnostica o Cowork; o CLI aparece na lista de stores de todo jeito.
# Sem instalação em nenhum, cai no mais recente. Antes o doctor pegava só o
# 1º store e dizia "nada urgente" com um plugin de março instalado em outro.
with_install = [i for i in inspections if i["plugin_installed"]]
cowork_installed = [i for i in with_install if "cowork_plugins" in i["root"]]
target = (
    cowork_installed[0]
    if cowork_installed
    else (with_install[0] if with_install else (inspections[0] if inspections else None))
)

# Drift plugin↔workspace (#179 PR9): o core do workspace declara a versão
# que o usuário REALMENTE usa; plugin instalado ≠ core = as duas pontas da
# experiência rodando produto diferente.
workspace_core_version = None
plugin_workspace_drift = None
workspace_note = None
workspace_action = None
if workspace_arg:
    workspace_path = Path(workspace_arg).expanduser()
    workspace_core_version = read_workspace_core_version(workspace_path)
    installed_now = target["plugin_version"] if target else None
    if workspace_core_version is None:
        workspace_note = "Workspace informado, mas o core (.prumo/system/PRUMO-CORE.md) não foi lido — sem drift calculável."
    elif installed_now:
        plugin_workspace_drift = installed_now != workspace_core_version
        if plugin_workspace_drift:
            newer = "plugin" if semver_tuple(installed_now) > semver_tuple(workspace_core_version) else "workspace"
            workspace_note = (
                f"Drift plugin↔workspace: plugin instalado {installed_now}, core do workspace {workspace_core_version} "
                f"(mais novo: {newer})."
            )
            if newer == "plugin":
                workspace_action = "Rode `prumo repair --workspace <path>` (ou o update do runtime) pra realinhar o core do workspace com o plugin."
            else:
                workspace_action = "Atualize o plugin no host (marketplace → reinstalar) pra alcançar o core do workspace."
    else:
        workspace_note = "Workspace tem core, mas nenhum plugin instalado foi encontrado nos stores — sem drift calculável."

result = {
    "sessions_root": str(sessions_root),
    "roots_found": len(roots),
    "target_root": target["root"] if target else None,
    "marketplace_name": marketplace_name,
    "plugin_id": plugin_id,
    "offline": offline,
    "workspace_path": str(Path(workspace_arg).expanduser()) if workspace_arg else None,
    "workspace_core_version": workspace_core_version,
    "plugin_workspace_drift": plugin_workspace_drift,
    "workspace_note": workspace_note,
    "workspace_action": workspace_action,
    "caches": caches,
    "stale_caches": stale_caches,
    "roots": inspections,
}

if output_format == "json":
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0)

print("==> Prumo Cowork doctor")
print(f"Sessions root: {sessions_root}")
print(f"Cowork stores encontrados: {len(roots)}")

if not target:
    print()
    print("Não encontrei nenhum store de plugins do Cowork neste caminho.")
    print("Se o app estiver em outro perfil ou máquina, o problema não é botar fé no botão. É o caminho estar errado.")
    raise SystemExit(1)

print(f"Store alvo: {target['root']}")
if len(inspections) > 1:
    print()
    print("Stores inspecionados")
    for item in inspections:
        marker = "← alvo" if item is target else ""
        installed_desc = item["plugin_version"] or ("—" if not item["plugin_installed"] else "?")
        print(f"- {item['root']} · plugin instalado: {installed_desc} {marker}".rstrip())
print()
print("Marketplace")
print(f"- conhecido: {'sim' if target['marketplace_known'] else 'não'}")
if target["marketplace_source"]:
    print(f"- source: {json.dumps(target['marketplace_source'], ensure_ascii=False)}")
print(f"- lastUpdated: {target['marketplace_last_updated'] or 'n/d'}")
print(f"- checkout: {target['marketplace_checkout_path'] or 'n/d'}")
print(f"- branch: {target['marketplace_checkout_branch'] or 'n/d'}")
print(f"- HEAD local: {(target['marketplace_checkout_head'] or 'n/d')[:7] if target['marketplace_checkout_head'] else 'n/d'}")
print(f"- versão no checkout: {target['marketplace_checkout_version'] or 'n/d'}")
print(f"- versão anunciada no marketplace: {target['marketplace_declared_plugin_version'] or 'n/d'}")
print(f"- HEAD remoto: {(target['marketplace_remote_head'] or 'n/d')[:7] if target['marketplace_remote_head'] else 'n/d'}")
if target["marketplace_checkout_stale"] is None:
    print("- checkout defasado: n/d")
else:
    print(f"- checkout defasado: {'sim' if target['marketplace_checkout_stale'] else 'não'}")
if target.get("marketplace_checkout_divergence") == "divergente":
    print("- natureza: o checkout DIVERGIU do remoto (sem ancestral comum — história do espelho reescrita)")
elif target.get("marketplace_checkout_divergence") == "commits_locais":
    print("- natureza: commits locais no checkout (fast-forward impossível; update não vai resetar)")
elif target.get("marketplace_checkout_divergence") == "atras":
    print("- natureza: atrás do remoto (fast-forward possível)")

print()
print("Plugin")
print(f"- instalado: {'sim' if target['plugin_installed'] else 'não'}")
print(f"- versão instalada: {target['plugin_version'] or 'n/d'}")
print(f"- commit instalado: {(target['plugin_git_commit'] or 'n/d')[:7] if target['plugin_git_commit'] else 'n/d'}")
print(f"- installPath: {target['plugin_install_path'] or 'n/d'}")
print(f"- repo local desta cópia do Prumo: {target['expected_repo_version'] or 'n/d'}")
print(f"- update recomendado pelo catálogo local: {'sim' if target['plugin_update_recommended'] else 'não'}")
if target["skills_content_drift"] is not None:
    print(f"- skills instaladas == checkout (hash agregado): {'NÃO' if target['skills_content_drift'] else 'sim'}")

if workspace_arg:
    print()
    print("Workspace")
    print(f"- caminho: {result['workspace_path']}")
    print(f"- versão do core: {workspace_core_version or 'n/d'}")
    if plugin_workspace_drift is None:
        print("- drift plugin↔workspace: n/d")
    else:
        print(f"- drift plugin↔workspace: {'SIM' if plugin_workspace_drift else 'não'}")
    if workspace_note:
        print(f"- nota: {workspace_note}")

if caches:
    print()
    print("Caches")
    for entry in caches:
        size_mb = entry["bytes"] / (1024 * 1024)
        print(f"- {entry['version']} · {size_mb:.1f} MB · {entry['status']} · {entry['path']}")
    if stale_caches:
        print("  Remoção (colar no terminal — o doctor NUNCA remove sozinho):")
        for entry in stale_caches:
            print(f"    {entry['remove_command']}")

if target["diagnosis"] or workspace_note:
    print()
    print("Diagnóstico")
    for item in target["diagnosis"]:
        print(f"- {item}")
    if workspace_note:
        print(f"- {workspace_note}")

final_actions = list(target["recommended_actions"])
if workspace_action:
    final_actions.append(workspace_action)
if stale_caches:
    total_mb = sum(c["bytes"] for c in stale_caches) / (1024 * 1024)
    final_actions.append(
        f"Caches antigos somam {total_mb:.1f} MB — os comandos de remoção prontos estão na seção Caches acima."
    )

print()
print("Próxima ação")
if final_actions:
    for index, item in enumerate(final_actions, start=1):
        print(f"{index}. {item}")
else:
    print("1. Nada urgente. O runtime do Cowork e o catálogo local parecem alinhados.")
PY
