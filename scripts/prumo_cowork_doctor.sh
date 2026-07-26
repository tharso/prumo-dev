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
  1. Localiza os stores reais de plugins e os CLASSIFICA (#190): a store atual é a unificada
     ~/.claude/plugins; ~/.claude/cowork_plugins e os cowork_plugins de sessão são LEGADO morto
     (marcados, nunca alvo havendo alternativa instalada)
  2. Inspeciona o checkout do marketplace usado pelo Cowork
  3. Compara versão do plugin instalado, versão do checkout local e HEAD remoto do repositório
  4. Flagra plugin de era antiga (pré-5.x) e catálogo fresco com instalação defasada
  5. Com --workspace: drift plugin↔workspace (prumo_version do core vs plugin instalado) (#179 PR9)
  6. Enumera caches de plugin (cache/<mkt>/<plugin>/<versão>) com bytes e comando de remoção PRONTO — nunca executa
  7. Hash agregado das árvores de skills (checkout vs instalado) — drift de conteúdo com versões iguais
  8. Inspeciona a CAMADA DE SESSÃO (#190): o que o registro server-side da conta materializa em
     <sessão>/<id>/rpm/ — divergência do marketplace é nomeada com o updatedAt do registro, e a
     prescrição é a validada: re-add como owner/repo (URL raw é rejeitada pela UI), sessão nova

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
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
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


def is_single_component(value):
    return bool(value) and value not in {".", ".."} and not any(c in value for c in ("/", "\\", "\0"))


def require_single_component(label, value):
    # Review Codex (round 3): nome com separador ou '..' construiria paths
    # FORA do store (root/marketplaces/<nome>, cache/<mkt>/<plugin>). Nome é
    # componente único ou nada.
    if not is_single_component(value):
        print(f"{label} inválido (tem que ser um único componente de path): {value!r}", file=sys.stderr)
        raise SystemExit(2)


require_single_component("--marketplace-name", marketplace_name)
require_single_component("--plugin-id (parte antes do @)", plugin_name)


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


def derive_version_probe_url(manifest_url: str):
    # Deriva a URL do VERSION publicado ao lado do manifesto. Query/fragment
    # caem fora; URL .git é git disfarçado de url — sem probe.
    try:
        parsed = urllib.parse.urlparse(manifest_url)
    except ValueError:
        return None
    if not parsed.scheme or not parsed.path:
        return None
    path = parsed.path
    if path.endswith(".git"):
        return None
    if path.endswith(".json"):
        path = path.rsplit("/", 1)[0]
    base_path = path.rstrip("/")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, f"{base_path}/VERSION", "", "", ""))


def fetch_url_version(url: str, timeout: float = 1.5):
    # Staleness pra marketplace com source "url" (#179 PR9): busca o VERSION
    # publicado ao lado do manifesto, com timeout curto — doctor não pode
    # pendurar num DNS morto. Qualquer falha → None (sem rede não é erro).
    # Resposta que não parseia como semver também é None: comparar lixo
    # marcaria stale falso.
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            value = resp.read(256).decode("utf-8", errors="replace").strip()
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return value if semver_tuple(value) else None


def readd_recipe(source):
    # Receita VALIDADA no incidente de 2026-07-15/16 (#190): só identidade
    # NOVA no servidor (fonte git owner/repo) força clone fresco; a UI atual
    # rejeita URL raw ("Este host não é suportado").
    repo = None
    if isinstance(source, dict) and source.get("source") == "github":
        repo = source.get("repo")
    form = f"`{repo}`" if repo else "`owner/repo` (ex.: `tharso/prumo`)"
    recipe = (
        f"Remova o marketplace INTEIRO na UI, re-adicione como {form} "
        "(formato owner/repo — o formulário atual REJEITA URL raw), reinstale o plugin e teste em SESSÃO NOVA."
    )
    if shutil.which("claude"):
        recipe += f" Com a CLI no PATH, o reparo local é `claude plugin install {plugin_id}`."
    return recipe


def store_kind(root: Path):
    # Classificação das stores (#190): o Cowork atual usa a store UNIFICADA
    # (~/.claude/plugins, a mesma da CLI); ~/.claude/cowork_plugins e os
    # cowork_plugins de sessão são da era ≤março/2026 — mortos, nada mais
    # escreve neles. Legado NUNCA vira alvo se houver alternativa.
    name = root.name
    if "cowork_plugins" in root.as_posix():
        return "legacy_cowork"
    if name == "plugins" and root.parent.name == ".claude":
        return "unified"
    if name == "plugins" and root.parent.name == ".codex":
        return "codex"
    return "other"


def scan_session_materializations(base: Path):
    # Camada 5 da propagação (#190): sessões do Cowork NÃO leem store local —
    # materializam o plugin do REGISTRO SERVER-SIDE da conta em
    # <sessão>/<id>/rpm/plugin_<id>/, com um manifest.json índice em rpm/.
    # Profundidade fixa (sem rglob); symlink nunca atravessado — nem no rpm/,
    # nem no plugin_dir, nem no VERSION; o `id` do manifesto é dado NÃO
    # confiável e só entra no path como componente único revalidado por
    # resolve(). Falha de leitura/schema NÃO some: vira session_scan_errors.
    found = []
    errors = []
    if base.is_symlink() or not base.is_dir():
        return found, errors
    try:
        level1 = [d for d in base.iterdir() if d.is_dir() and not d.is_symlink()]
    except OSError as exc:
        errors.append({"path": str(base), "error": f"listagem falhou: {exc.__class__.__name__}"})
        return found, errors
    for outer in level1:
        try:
            level2 = [d for d in outer.iterdir() if d.is_dir() and not d.is_symlink()]
        except OSError as exc:
            errors.append({"path": str(outer), "error": f"listagem falhou: {exc.__class__.__name__}"})
            continue
        for inner in level2:
            rpm_dir = inner / "rpm"
            if rpm_dir.is_symlink():
                errors.append({"path": str(rpm_dir), "error": "rpm/ é symlink — não atravessado"})
                continue
            manifest_path = rpm_dir / "manifest.json"
            if manifest_path.is_symlink():
                errors.append({"path": str(manifest_path), "error": "manifest.json é symlink — não lido"})
                continue
            if not manifest_path.is_file():
                continue
            try:
                manifest = read_json(manifest_path)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append({"path": str(manifest_path), "error": f"manifest ilegível: {exc.__class__.__name__}"})
                continue
            plugins = manifest.get("plugins") if isinstance(manifest, dict) else None
            if not isinstance(plugins, list):
                errors.append({"path": str(manifest_path), "error": "schema inesperado: sem lista `plugins`"})
                continue
            for entry in plugins:
                if not isinstance(entry, dict):
                    errors.append({"path": str(manifest_path), "error": f"entrada não-objeto na lista `plugins`: {type(entry).__name__}"})
                    continue
                if entry.get("name") != plugin_name:
                    continue
                entry_id = entry.get("id")
                if not isinstance(entry_id, str) or not is_single_component(entry_id):
                    # ID ausente/não-string/não-componente: entrada IGNORADA
                    # com rastro — sem id não há materialização que valha.
                    errors.append({"path": str(manifest_path), "error": f"id de plugin ausente ou suspeito no manifesto: {entry_id!r}"})
                    continue
                version = None
                plugin_dir = rpm_dir / entry_id
                version_file = plugin_dir / "VERSION"
                try:
                    inside = True
                    try:
                        plugin_dir.resolve().relative_to(rpm_dir.resolve())
                    except ValueError:
                        inside = False
                    if (
                        inside
                        and not plugin_dir.is_symlink()
                        and plugin_dir.is_dir()
                        and not version_file.is_symlink()
                        and version_file.is_file()
                    ):
                        version = read_text(version_file)
                except OSError:
                    version = None
                updated_at = entry.get("updatedAt")
                if updated_at is not None and not isinstance(updated_at, str):
                    # Não-string quebraria o sort — normaliza e deixa rastro.
                    errors.append({"path": str(manifest_path), "error": f"updatedAt não-string no manifesto: {updated_at!r}"})
                    updated_at = None
                found.append({
                    "session_path": str(inner),
                    "plugin_id": entry_id,
                    "updated_at": updated_at,
                    "updated_at_verified": entry.get("updatedAtVerified"),
                    "marketplace_name": entry.get("marketplaceName"),
                    "version": version,
                })
    found.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return found, errors


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
    # Statuses:
    #   em_uso        → installPath registrado aponta EXATAMENTE pra este path
    #   stale         → nada referencia; comando de remoção emitido
    #   indeterminado → mesma VERSÃO de uma instalação, mas nenhum installPath
    #                   aponta pra cá (duplicata provável) — visível, sem comando
    #   suspeito      → symlink na cadeia ou resolve fora do store — NUNCA
    #                   ganha comando: rm através de symlink apontaria pra fora
    caches = []
    seen = set()
    for base in bases:
        # Cadeia sem symlink (postura do sanitize, #179), checada ANTES de
        # qualquer listagem: symlink não é atravessado nem pra contar bytes.
        # Um diagnóstico único "suspeito" e nada de filhos/comando.
        symlinked = None
        if base.is_symlink():
            symlinked = base
        else:
            probe = base
            for part in ("cache", marketplace_name, plugin_name):
                probe = probe / part
                if probe.is_symlink():
                    symlinked = probe
                    break
        if symlinked is not None:
            caches.append({
                "root": str(base),
                "path": str(symlinked),
                "version": None,
                "bytes": None,
                "status": "suspeito",
                "remove_command": None,
            })
            continue
        cache_dir = base / "cache" / marketplace_name / plugin_name
        base_resolved = base.resolve()
        # Defesa em profundidade: mesmo com nomes validados, só listar se o
        # cache_dir resolvido continua DENTRO do store.
        try:
            cache_dir.resolve().relative_to(base_resolved)
        except ValueError:
            continue
        if not cache_dir.is_dir():
            continue
        for vdir in sorted(cache_dir.iterdir()):
            if vdir.is_symlink() or not vdir.is_dir():
                continue
            resolved = vdir.resolve()
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            inside_store = True
            try:
                resolved.relative_to(base_resolved)
            except ValueError:
                inside_store = False
            if not inside_store:
                status = "suspeito"
            elif key in protected_paths:
                status = "em_uso"
            elif vdir.name in protected_versions or not semver_tuple(vdir.name):
                # Sem semver no nome (tmp, current, download parcial) não há
                # como afirmar staleness — visível, sem comando às cegas.
                status = "indeterminado"
            else:
                status = "stale"
            caches.append({
                "root": str(base),
                "path": str(vdir),
                "version": vdir.name,
                "bytes": dir_size_bytes(vdir),
                "status": status,
                "remove_command": f"rm -rf {shlex.quote(str(vdir))}" if status == "stale" else None,
            })
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
    remote_version = None
    remote_version_source = None
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
            probe_url = derive_version_probe_url(source.get("url") or "")
            if probe_url:
                remote_version = fetch_url_version(probe_url)
                if remote_version:
                    remote_version_source = "url"
            if remote_version and semver_tuple(checkout_version):
                checkout_stale = semver_tuple(remote_version) != semver_tuple(checkout_version)
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
        actions.append(readd_recipe(source))
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
            "Reinstalação simples pode devolver o MESMO catálogo fóssil (registro da conta congelado, #190). "
            + readd_recipe(source)
        )

    expected_repo_version = None
    version_file = repo_root / "VERSION"
    if version_file.exists():
        expected_repo_version = read_text(version_file)

    return {
        "root": str(root),
        "store_kind": store_kind(root),
        "marketplace_known": bool(marketplace_entry),
        "marketplace_source": source,
        "marketplace_last_updated": last_updated,
        "marketplace_checkout_path": str(install_location) if install_location else None,
        "marketplace_checkout_branch": checkout_branch,
        "marketplace_checkout_head": checkout_head,
        "marketplace_checkout_version": checkout_version,
        "marketplace_declared_plugin_version": checkout_declared_version,
        "marketplace_remote_head": remote_head,
        "marketplace_remote_version": remote_version,
        "marketplace_remote_version_source": remote_version_source,
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
cache_anomalies = [c for c in caches if c["status"] in {"suspeito", "indeterminado"}]
# Target = o store onde o plugin está INSTALADO (é lá que a invocação resolve).
# Precedência (#190, INVERTE a regra do #146): o Cowork atual opera sobre a
# store UNIFICADA (~/.claude/plugins); cowork_plugins é legado morto e NUNCA
# vira alvo havendo alternativa instalada — mirar nele foi o que prescreveu
# reparo inútil no incidente de 15-16/07. Sem instalação em nenhum, cai no
# mais recente (comportamento de antes).
with_install = [i for i in inspections if i["plugin_installed"]]
_KIND_ORDER = {"unified": 0, "other": 1, "codex": 2, "legacy_cowork": 3}
with_install.sort(key=lambda i: _KIND_ORDER.get(i["store_kind"], 1))
# Fallback sem instalação TAMBÉM respeita a classe (review Codex): mtime só
# desempata dentro da mesma classe (sort estável sobre a ordem de mtime do
# collect_roots) — senão uma legada recém-tocada voltaria a ser alvo.
no_install_sorted = sorted(inspections, key=lambda i: _KIND_ORDER.get(i["store_kind"], 1))
target = with_install[0] if with_install else (no_install_sorted[0] if no_install_sorted else None)

legacy_stores = [i["root"] for i in inspections if i["store_kind"] == "legacy_cowork"]
legacy_note = None
if legacy_stores:
    legacy_note = (
        "Store legada presente (era ≤março/2026, nada mais escreve nela): "
        + "; ".join(legacy_stores)
        + " — entulho removível; o Cowork atual usa a store unificada ~/.claude/plugins e o registro da conta (#190)."
    )
if target is not None and target["store_kind"] == "legacy_cowork":
    legacy_note = (
        (legacy_note + " ATENÇÃO: o plugin SÓ está instalado na store legada — instale pela store atual do host. ")
        if legacy_note
        else ""
    ) + readd_recipe(target.get("marketplace_source"))

# Camada de sessão (#190): o que a conta REALMENTE materializa nas sessões
# do Cowork. Divergência da melhor referência local = o mecanismo do
# incidente (registro server-side parado) — nomeada com o updatedAt.
session_materializations, session_scan_errors = scan_session_materializations(sessions_root)
session_latest = session_materializations[0] if session_materializations else None
session_divergence = None
session_reference = None
session_note = None
session_action = None
if session_latest and session_latest.get("version") and target is not None:
    # Referência por ELO da cadeia de distribuição: sessão compara com o
    # marketplace (checkout/catálogo/remoto-url); o drift do checkout contra
    # o remoto git tem elo próprio, e o repo dev desta cópia fica FORA — é
    # outra camada (aparece no painel como informação, não como régua).
    candidates = [
        ("checkout do marketplace", target.get("marketplace_checkout_version")),
        ("catálogo do marketplace", target.get("marketplace_declared_plugin_version")),
        ("VERSION remoto (url)", target.get("marketplace_remote_version")),
    ]
    candidates = [(label, v) for label, v in candidates if v and semver_tuple(v)]
    if candidates:
        ref_label, ref_version = max(candidates, key=lambda pair: semver_tuple(pair[1]))
        session_reference = {"label": ref_label, "version": ref_version}
        if semver_tuple(session_latest["version"]) < semver_tuple(ref_version):
            session_divergence = True
            session_note = (
                f"A sessão materializa {session_latest['version']} (registro da conta, "
                f"updatedAt {session_latest.get('updated_at') or 'n/d'}), atrás de {ref_version} ({ref_label}). "
                "Se o updatedAt está parado no passado, é o registro server-side congelado do #190 — "
                "reinstalação simples re-vincula o registro velho."
            )
            session_action = readd_recipe(target.get("marketplace_source"))
        else:
            session_divergence = False

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
                # O repair grava o core DA VERSÃO DO RUNTIME instalado —
                # runtime velho regravaria o mesmo core velho. Runtime
                # primeiro, repair depois.
                workspace_action = (
                    f"Atualize o runtime local até ≥ {installed_now} (`prumo update` ou reinstalação) "
                    "e SÓ ENTÃO rode `prumo repair --workspace <path>` — repair com runtime velho regrava o core velho."
                )
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
    "cache_anomalies": cache_anomalies,
    "legacy_stores": legacy_stores,
    "legacy_note": legacy_note,
    "session_materializations": session_materializations,
    "session_scan_errors": session_scan_errors,
    "session_reference": session_reference,
    "session_divergence": session_divergence,
    "session_note": session_note,
    "session_action": session_action,
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
    _KIND_LABEL = {"unified": "store atual (unificada)", "legacy_cowork": "LEGADA (morta)", "codex": "codex", "other": "outra"}
    for item in inspections:
        marker = "← alvo" if item is target else ""
        installed_desc = item["plugin_version"] or ("—" if not item["plugin_installed"] else "?")
        kind = _KIND_LABEL.get(item["store_kind"], item["store_kind"])
        print(f"- {item['root']} · {kind} · plugin instalado: {installed_desc} {marker}".rstrip())
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

if session_latest or session_scan_errors:
    print()
    print("Sessão (registro da conta)")
    if session_latest:
        print(f"- materializada: {session_latest.get('version') or 'n/d'} · updatedAt: {session_latest.get('updated_at') or 'n/d'}")
        if session_reference:
            print(f"- referência local mais fresca: {session_reference['version']} ({session_reference['label']})")
        if session_divergence is None:
            print("- divergência: n/d")
        else:
            print(f"- divergência: {'SIM' if session_divergence else 'não'}")
    if session_scan_errors:
        print(f"- varredura INCOMPLETA: {len(session_scan_errors)} erro(s) de leitura/schema — camada 5 indeterminada nesses pontos (detalhe no --json)")

if caches:
    print()
    print("Caches")
    for entry in caches:
        size = f"{entry['bytes'] / (1024 * 1024):.1f} MB" if entry["bytes"] is not None else "n/d"
        label = entry["version"] or "cadeia com symlink"
        print(f"- {label} · {size} · {entry['status']} · {entry['path']}")
    if stale_caches:
        print("  Remoção (colar no terminal — o doctor NUNCA remove sozinho):")
        for entry in stale_caches:
            print(f"    {entry['remove_command']}")

if target["diagnosis"] or workspace_note or legacy_note or session_note:
    print()
    print("Diagnóstico")
    for item in target["diagnosis"]:
        print(f"- {item}")
    if workspace_note:
        print(f"- {workspace_note}")
    if legacy_note:
        print(f"- {legacy_note}")
    if session_note:
        print(f"- {session_note}")

final_actions = list(target["recommended_actions"])
if workspace_action:
    final_actions.append(workspace_action)
if session_action and session_action not in final_actions:
    final_actions.append(session_action)
if stale_caches:
    total_mb = sum(c["bytes"] for c in stale_caches) / (1024 * 1024)
    final_actions.append(
        f"Caches antigos somam {total_mb:.1f} MB — os comandos de remoção prontos estão na seção Caches acima."
    )
suspicious = [c for c in cache_anomalies if c["status"] == "suspeito"]
undetermined = [c for c in cache_anomalies if c["status"] == "indeterminado"]
if suspicious:
    final_actions.append(
        f"{len(suspicious)} entrada(s) de cache SUSPEITAS (symlink na cadeia ou path fora do store) — "
        "inspecione à mão antes de qualquer coisa; o doctor não monta comando pra elas de propósito."
    )
if undetermined:
    final_actions.append(
        f"{len(undetermined)} entrada(s) de cache indeterminadas (duplicata da versão instalada ou nome fora do padrão) — "
        "confira a origem à mão; sem certeza, nada de rm."
    )

print()
print("Próxima ação")
if final_actions:
    for index, item in enumerate(final_actions, start=1):
        print(f"{index}. {item}")
else:
    print("1. Nada urgente. O runtime do Cowork e o catálogo local parecem alinhados.")
PY
