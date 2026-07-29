"""Executor determinístico da sanitização técnica (#179, épico #177).

O módulo `sanitize.md` sempre foi a superfície do agente (#172) e antecipava
o subcomando: "Quando o runtime do Prumo oferecer um subcomando dedicado,
este documento ganha a chamada correspondente". Este é o motor: detecção
pura (`build_plan`, read-only) e execução (`apply_plan`), que consome o
PLANO APROVADO do dry-run: re-detecta fresco e só executa item que estava no
plano e continua idêntico (fingerprint por item). Item novo, alterado ou
sumido vira `blocked` — o que roda é exatamente o que foi aprovado.

Escopo: `.prumo/**` e o legado flat `_state/**`. `Prumo/` (dado do usuário)
nunca entra num plano por construção, e a execução ainda valida cada path
contra o escopo antes de tocar. Symlink — o próprio candidato ou qualquer
ancestral dele até a raiz do workspace — nunca entra no plano nem é
atravessado: enumerar, ler, hashear, mover e apagar exigem cadeia limpa.
Nunca roda automático: dry-run é o default do CLI e o apply exige o plano
aprovado + `--yes`.

Regras (cada path pertence a NO MÁXIMO uma, na ordem daqui):

- `agente_rascunho`      → move pro backup (filho direto frio de
                           `.prumo/state/rascunho/`, #263). Subtree EXCLUSIVA:
                           nenhuma outra regra a reivindica, mesmo isolada.
- `handover_legacy`      → move pro backup (formato aposentado, #68)
- `decidir_ephemeral`    → move pro backup (HTML/fonte >14d, contrato #102)
- `nested_backups`       → delete (backup dentro de backup é redundância;
                           copiar recriaria o problema)
- `expired_backups`      → delete (>90d; backup expirado não ganha backup)
- `legacy_backup_consolidation` → move pra `.prumo/backups/legacy/` (#81)
- `workspace_cache`      → delete (cache é reproduzível)
- `asset_dedupe`         → delete (fonte em state/ com SHA-256 idêntico à
                           vendored e não referenciada por HTML sobrevivente;
                           o "backup" é a própria vendored)

Backup único do apply: `.prumo/backups/sanitize/<stamp>/`, populado por
`shutil.move` com o path achatado pela convenção `__` do runtime-migrate
(`_state/HANDOVER.md` → `_state__HANDOVER.md`) — sem diretório de backup
dentro do backup por construção. O achatamento não é bijetivo (`a/b` e
`a__b` colidem): destino que já existe vira `blocked`, nunca sobrescrita, e
o mapa autoritativo from→to é o journal + ARCHIVE-INDEX, não o nome. Antes
da primeira mutação o ARCHIVE-INDEX é validado (corrompido → aborta) e o
journal write-ahead é gravado no stamp; os índices são escritos de forma
atômica (tmp + replace). Nunca copytree. O plano congela ANTES de o stamp
existir, então ele nunca se lista.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from prumo_runtime import faxina_thresholds
from prumo_runtime.agente_rascunho import (
    _sob_rascunho,
    iter_agente_rascunho,
)
from prumo_runtime.scan_primitives import (
    _age_days,
    _clean_chain,
    _content_id,
    _mtime_ns,
    _rel,
    _sha256,
    _size_bytes,
    _tree_has_symlink,
    _usable_root,
    _walk_tree,
)
from prumo_runtime.backup import iter_backup_roots

SCHEMA_VERSION = "prumo_sanitize_report.v1"

RULES = (
    "agente_rascunho",
    "handover_legacy",
    "decidir_ephemeral",
    "nested_backups",
    "expired_backups",
    "legacy_backup_consolidation",
    "workspace_cache",
    "asset_dedupe",
)

_FONT_SUFFIXES = {".otf", ".ttf", ".woff", ".woff2"}
_EPHEMERAL_SUFFIXES = _FONT_SUFFIXES | {".html"}
_PRESERVED_NAMES = {"workspace-schema.json", "agent-lock.json"}
_BACKUP_DIR_NAMES = {".prumo", "backup", "backups"}
_ABSOLUTE_PATH = re.compile(r"^(/|[A-Za-z]:[\\/])")
_FINGERPRINT_KEYS = ("rule", "path", "action", "size_bytes", "mtime_ns", "sha256")


class SanitizeError(RuntimeError):
    """Erro controlado do executor (vira exit 2 no CLI, sem traceback)."""


@dataclass(frozen=True)
class Thresholds:
    # #258: os dois que moram na tabela do `faxina-thresholds.md` vêm da fonte
    # única; `ephemeral_days` é só daqui (não está no doc).
    ephemeral_days: int = 14
    backup_expiry_days: int = faxina_thresholds.DEFAULTS["backup_expiry_days"]
    cache_days: int = faxina_thresholds.DEFAULTS["cache_expiry_days"]

    def validate(self) -> None:
        for name in ("ephemeral_days", "backup_expiry_days", "cache_days"):
            if getattr(self, name) < 0:
                raise SanitizeError(f"threshold negativo: {name}={getattr(self, name)}")


def _under_backup_root(workspace: Path, path: Path) -> bool:
    return any(
        root in path.parents for root in iter_backup_roots(workspace)
    )


# --- Detectores puros (reusados pelo /fim, read-only) -----------------------


def iter_handover_files(workspace: Path) -> list[Path]:
    """Arquivos HANDOVER* sob `.prumo/state/**` e `_state/**` (formato
    aposentado, #68). Nunca dentro dos backup roots (lá é território das
    regras de backup), **nunca dentro do rascunho do agente** (#263 — a
    exclusão precisa morar AQUI, não só no `build_plan`: o `/fim` consome o
    iterator direto, e um rascunho chamado `HANDOVER-x.md` disparava
    `handover_legacy` no painel) e nunca através de symlink."""
    found: list[Path] = []
    for root in (workspace / ".prumo" / "state", workspace / "_state"):
        if not _usable_root(workspace, root):
            continue
        _, files = _walk_tree(root)
        for path in files:
            if (
                path.name.startswith("HANDOVER")
                and not _under_backup_root(workspace, path)
                and not _sob_rascunho(workspace, path)
            ):
                found.append(path)
    return found


def iter_nested_backup_dirs(workspace: Path) -> list[Path]:
    """Diretórios de backup DENTRO de um backup root (`.prumo`, `backup`,
    `backups`) — só os top-most, pra remoção atômica."""
    nested: list[Path] = []
    for root in iter_backup_roots(workspace):
        if not _usable_root(workspace, root):
            continue
        dirs, _ = _walk_tree(root)
        for path in dirs:
            if path.name not in _BACKUP_DIR_NAMES:
                continue
            if any(parent in nested for parent in path.parents):
                continue  # já coberto por um ancestral detectado
            nested.append(path)
    return nested


def _iter_expired_backups(workspace: Path, today: date, expiry_days: int) -> list[Path]:
    expired: list[Path] = []
    for root in iter_backup_roots(workspace):
        if not _usable_root(workspace, root):
            continue
        if root.name == "backups":
            scopes = [s for s in sorted(root.iterdir()) if not s.is_symlink() and s.is_dir()]
            entries = [e for scope in scopes for e in sorted(scope.iterdir()) if not e.is_symlink()]
        else:
            entries = [e for e in sorted(root.iterdir()) if not e.is_symlink()]
        for entry in entries:
            if _age_days(entry, today) > expiry_days:
                expired.append(entry)
    return expired


def _iter_legacy_survivors(workspace: Path, today: date, expiry_days: int) -> list[Path]:
    legacy_root = workspace / ".prumo" / "backup"
    if not _usable_root(workspace, legacy_root):
        return []
    return [
        entry
        for entry in sorted(legacy_root.iterdir())
        if not entry.is_symlink() and _age_days(entry, today) <= expiry_days
    ]


def _iter_old_cache(workspace: Path, today: date, cache_days: int) -> list[Path]:
    cache_root = workspace / ".prumo" / "cache"
    if not _usable_root(workspace, cache_root):
        return []
    _, files = _walk_tree(cache_root)
    return [path for path in files if _age_days(path, today) > cache_days]


def _iter_old_ephemerals(workspace: Path, today: date, ephemeral_days: int) -> list[Path]:
    found: list[Path] = []
    for sub in ("decidir", "acervo"):
        root = workspace / ".prumo" / "state" / sub
        if not _usable_root(workspace, root):
            continue
        _, files = _walk_tree(root)
        for path in files:
            if path.suffix.lower() not in _EPHEMERAL_SUFFIXES:
                continue
            if path.name.startswith("HANDOVER"):
                continue  # território da handover_legacy
            if _age_days(path, today) > ephemeral_days:
                found.append(path)
    return found


def _iter_duplicate_assets(workspace: Path, claimed: set[str]) -> list[tuple[Path, str]]:
    """Fontes em `.prumo/state/**` com hash idêntico a uma vendored em
    `.prumo/skills/**/assets/**` e não referenciadas por HTML sobrevivente.
    Nada é enumerado, lido ou hasheado através de symlink."""
    skills_root = workspace / ".prumo" / "skills"
    state_root = workspace / ".prumo" / "state"
    if not _usable_root(workspace, skills_root) or not _usable_root(workspace, state_root):
        return []
    _, skills_files = _walk_tree(skills_root)
    vendored_hashes = {
        _sha256(path)
        for path in skills_files
        if path.suffix.lower() in _FONT_SUFFIXES and "assets" in path.parts
    }
    if not vendored_hashes:
        return []
    _, state_files = _walk_tree(state_root)
    surviving_html_text = ""
    for html in state_files:
        if html.suffix.lower() != ".html":
            continue
        if _rel(workspace, html) in claimed or _under_backup_root(workspace, html):
            continue
        surviving_html_text += html.read_text(encoding="utf-8", errors="ignore")

    duplicates: list[tuple[Path, str]] = []
    for path in state_files:
        rel = _rel(workspace, path)
        if rel in claimed:
            continue
        if path.suffix.lower() not in _FONT_SUFFIXES or _under_backup_root(workspace, path):
            continue
        digest = _sha256(path)
        if digest not in vendored_hashes:
            continue
        if path.name in surviving_html_text:
            continue
        duplicates.append((path, digest))
    return duplicates


# --- Plano e execução --------------------------------------------------------


def _preserved(workspace: Path, path: Path) -> bool:
    """Preservação por CAMINHO canônico, não por basename global.

    Antes, um rascunho chamado `agent-lock.json` ou guardado sob qualquer
    pasta `logs/` nunca seria limpo — contrariando "sem filtro de sufixo"
    (Codex, 263-6).
    """
    rel = _rel(workspace, path)
    if rel.startswith(".prumo/logs/") or rel == ".prumo/logs":
        return True
    return rel in {f".prumo/state/{nome}" for nome in _PRESERVED_NAMES}


def build_plan(
    workspace: Path,
    *,
    today: date | None = None,
    thresholds: Thresholds | None = None,
    rules: list[str] | None = None,
) -> dict:
    """Detecção pura (read-only). Cada path entra em no máximo uma regra.

    `rules=None` = todas; lista explícita vazia é erro (aprovação seletiva
    nunca pode "expandir" pra tudo por acidente).
    """
    workspace = workspace.expanduser().resolve()
    today = today or date.today()
    t = thresholds or Thresholds()
    t.validate()
    if rules is None:
        wanted = set(RULES)
    else:
        wanted = {rule for rule in rules if rule}
        if not wanted:
            raise SanitizeError("seleção de regras vazia — nomeie as regras ou omita `--rules`")
    for rule in wanted:
        if rule not in RULES:
            raise SanitizeError(f"regra desconhecida: {rule!r} (válidas: {', '.join(RULES)})")

    items: list[dict] = []
    claimed: set[str] = set()

    def _claim(rule: str, path: Path, action: str, reason: str, sha256: str | None = None) -> None:
        rel = _rel(workspace, path)
        if rel in claimed or _preserved(workspace, path):
            return
        if path.is_symlink() or _tree_has_symlink(path):
            return  # symlink (no item ou descendente) nunca entra no plano
        claimed.add(rel)
        items.append({
            "rule": rule,
            "path": rel,
            "size_bytes": _size_bytes(path),
            "age_days": _age_days(path, today),
            "mtime_ns": _mtime_ns(path),
            # Identidade forte: hash de conteúdo (arquivo) ou de manifesto
            # da árvore (diretório) — o apply só executa o que bater.
            "sha256": sha256 or _content_id(workspace, path),
            "action": action,
            "reason": reason,
        })

    if "agente_rascunho" in wanted:
        for path in iter_agente_rascunho(workspace, today, t.ephemeral_days):
            _claim(
                "agente_rascunho", path, "move-to-backup",
                f"rascunho do agente >{t.ephemeral_days}d (descartável por contrato)",
            )
    if "handover_legacy" in wanted:
        for path in iter_handover_files(workspace):
            if _sob_rascunho(workspace, path):
                continue  # subtree exclusiva do agente_rascunho (#263)
            _claim("handover_legacy", path, "move-to-backup", "formato HANDOVER aposentado (#68)")
    if "decidir_ephemeral" in wanted:
        for path in _iter_old_ephemerals(workspace, today, t.ephemeral_days):
            _claim(
                "decidir_ephemeral", path, "move-to-backup",
                f"efêmero de despacho >{t.ephemeral_days}d (reproduzível)",
            )
    if "nested_backups" in wanted:
        for path in iter_nested_backup_dirs(workspace):
            _claim("nested_backups", path, "delete", "backup dentro de backup (redundância)")
    if "expired_backups" in wanted:
        for path in _iter_expired_backups(workspace, today, t.backup_expiry_days):
            if _rel(workspace, path) in claimed:
                continue
            _claim(
                "expired_backups", path, "delete",
                f"backup >{t.backup_expiry_days}d (expirado não ganha backup)",
            )
    if "legacy_backup_consolidation" in wanted:
        for path in _iter_legacy_survivors(workspace, today, t.backup_expiry_days):
            _claim(
                "legacy_backup_consolidation", path, "consolidate",
                "legado `.prumo/backup/` → `.prumo/backups/legacy/` (#81)",
            )
    if "workspace_cache" in wanted:
        for path in _iter_old_cache(workspace, today, t.cache_days):
            _claim("workspace_cache", path, "delete", f"cache >{t.cache_days}d (reproduzível)")
    if "asset_dedupe" in wanted:
        for path, digest in _iter_duplicate_assets(workspace, claimed):
            if _sob_rascunho(workspace, path):
                continue  # subtree exclusiva do agente_rascunho (#263)
            _claim(
                "asset_dedupe", path, "delete",
                "hash idêntico à vendored em `.prumo/skills/**/assets/` e sem HTML vivo referenciando",
                sha256=digest,
            )

    by_rule: dict[str, dict] = {}
    for item in items:
        bucket = by_rule.setdefault(item["rule"], {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += item["size_bytes"]
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "dry-run",
        "workspace_path": str(workspace),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "thresholds": {
            "ephemeral_days": t.ephemeral_days,
            "backup_expiry_days": t.backup_expiry_days,
            "cache_days": t.cache_days,
        },
        "items": items,
        "totals": {
            "count": len(items),
            "bytes": sum(i["size_bytes"] for i in items),
            "by_rule": by_rule,
        },
    }


def _fingerprint(item: dict) -> tuple:
    return tuple(item.get(key) for key in _FINGERPRINT_KEYS)


def _atomic_write_text(path: Path, text: str) -> None:
    """Escrita atômica com temp EXCLUSIVO (mkstemp): nome imprevisível, fd
    próprio — um `.tmp` symlinkado plantado no diretório nunca é seguido."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _require_clean_write_target(workspace: Path, path: Path, label: str) -> None:
    """Cerca das SAÍDAS: destino de mkdir/write cujo componente existente
    (incluindo symlink QUEBRADO — exists() mente sobre eles) tenha symlink
    na cadeia, ou que resolva fora do workspace, é recusado — mover/escrever
    "pra dentro" de um symlink escreveria fora do território."""
    probe = path
    while (
        probe != workspace
        and workspace in probe.parents
        and not (probe.exists() or probe.is_symlink())
    ):
        probe = probe.parent
    if probe.is_symlink() or not _clean_chain(workspace, probe):
        raise SanitizeError(f"{label} atravessa symlink ({probe}) — recusado, nada executado")
    try:
        probe.resolve(strict=False).relative_to(workspace)
    except ValueError:
        raise SanitizeError(f"{label} resolve fora do workspace — recusado, nada executado")


def _preflight_archive(workspace: Path) -> tuple[dict, str]:
    """Valida o rastro ANTES de qualquer mutação: cadeia limpa do archive,
    JSON estrito (dict + entries lista de objetos) e MD legível. Corrompido
    ou fora da cerca → erro controlado com zero mutação (nunca substituir
    histórico por um índice vazio de fininho)."""
    archive_root = workspace / ".prumo" / "state" / "archive"
    _require_clean_write_target(workspace, archive_root, "ARCHIVE-INDEX (state/archive)")
    _require_clean_write_target(workspace, archive_root / "ARCHIVE-INDEX.json", "ARCHIVE-INDEX.json")
    _require_clean_write_target(workspace, archive_root / "ARCHIVE-INDEX.md", "ARCHIVE-INDEX.md")
    json_path = archive_root / "ARCHIVE-INDEX.json"
    payload: dict = {"schema_version": "1.0", "entries": []}
    if json_path.exists():
        try:
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SanitizeError(
                f"ARCHIVE-INDEX.json corrompido ({exc}) — corrija ou restaure antes de aplicar; "
                "nada foi movido nem removido"
            ) from exc
        if (
            not isinstance(loaded, dict)
            or not isinstance(loaded.get("entries", []), list)
            or not all(isinstance(e, dict) for e in loaded.get("entries", []))
        ):
            raise SanitizeError(
                "ARCHIVE-INDEX.json estruturalmente inválido (entries precisa ser lista de "
                "objetos) — nada foi executado"
            )
        loaded.setdefault("schema_version", "1.0")
        loaded.setdefault("entries", [])
        payload = loaded
    md_path = archive_root / "ARCHIVE-INDEX.md"
    md_text = "# Archive Index\n\n"
    if md_path.exists():
        try:
            md_text = md_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SanitizeError(f"ARCHIVE-INDEX.md ilegível ({exc}) — nada foi executado") from exc
    return payload, md_text


def _append_archive_index(
    workspace: Path,
    entries: list[dict],
    *,
    payload: dict | None = None,
    md_text: str | None = None,
) -> None:
    """Rastro obrigatório (ASSERT do core): paths RELATIVOS, json + md,
    escrita atômica."""
    for entry in entries:
        for key in ("from", "to"):
            value = entry.get(key)
            if value and _ABSOLUTE_PATH.match(str(value)):
                raise ValueError(
                    f"path absoluto em entrada do ARCHIVE-INDEX ({key}={value!r}) — "
                    "viola o contrato de portabilidade"
                )
    if payload is None or md_text is None:
        payload, md_text = _preflight_archive(workspace)
    archive_root = workspace / ".prumo" / "state" / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    payload["entries"].extend(entries)
    _atomic_write_text(
        archive_root / "ARCHIVE-INDEX.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    lines = []
    for entry in entries:
        destino = f"`{entry['to']}`" if entry.get("to") else "removido"
        lines.append(
            f"- {entry['at']} — {entry['op']}: `{entry['from']}` → {destino} ({entry['bytes']} bytes)"
        )
    _atomic_write_text(archive_root / "ARCHIVE-INDEX.md", md_text + "\n".join(lines) + "\n")


def _within_scope(workspace: Path, path: Path) -> bool:
    """Só `.prumo/**` e `_state/**`, com cadeia sem symlink e path resolvido
    dentro do escopo."""
    try:
        rel = path.relative_to(workspace)
    except ValueError:
        return False
    if not rel.parts or rel.parts[0] not in {".prumo", "_state"}:
        return False
    if not _clean_chain(workspace, path):
        return False
    try:
        resolved_rel = path.resolve().relative_to(workspace)
    except ValueError:
        return False
    return bool(resolved_rel.parts) and resolved_rel.parts[0] in {".prumo", "_state"}


def _validate_plan(workspace: Path, plan: dict) -> None:
    """Schema estrito do plano aprovado: qualquer desvio é SanitizeError com
    zero mutação — o plano é o vínculo de autorização, não um JSON qualquer."""
    if not isinstance(plan, dict) or plan.get("schema_version") != SCHEMA_VERSION:
        raise SanitizeError(
            f"plano inválido — esperado relatório {SCHEMA_VERSION} do dry-run"
        )
    if plan.get("mode") != "dry-run":
        raise SanitizeError(
            "plano precisa ser o relatório do DRY-RUN (mode: dry-run) — "
            "não reaproveite a saída de um apply"
        )
    plan_ws = plan.get("workspace_path")
    if not isinstance(plan_ws, str) or not plan_ws:
        raise SanitizeError("plano sem workspace_path — re-rode o dry-run")
    if Path(plan_ws) != workspace:
        raise SanitizeError(
            f"plano foi gerado pra outro workspace ({plan_ws}) — re-rode o dry-run aqui"
        )
    thresholds = plan.get("thresholds")
    if (
        not isinstance(thresholds, dict)
        or set(thresholds) != {"ephemeral_days", "backup_expiry_days", "cache_days"}
        or not all(isinstance(v, int) and v >= 0 for v in thresholds.values())
    ):
        raise SanitizeError("plano com thresholds inválidos — re-rode o dry-run")
    items = plan.get("items")
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise SanitizeError("plano com items inválidos — re-rode o dry-run")
    seen_paths: set[str] = set()
    for item in items:
        path = item.get("path")
        if (
            not isinstance(path, str)
            or not path
            or _ABSOLUTE_PATH.match(path)
            or ".." in Path(path).parts
            or path in seen_paths
        ):
            raise SanitizeError(f"plano com path inválido ou duplicado: {path!r}")
        seen_paths.add(path)
        if not isinstance(item.get("rule"), str) or item.get("rule") not in RULES:
            raise SanitizeError(f"plano com regra inválida em {path!r}")
        if item.get("action") not in {"move-to-backup", "consolidate", "delete"}:
            raise SanitizeError(f"plano com ação inválida em {path!r}")
        if not isinstance(item.get("size_bytes"), int) or not isinstance(item.get("mtime_ns"), int):
            raise SanitizeError(f"plano sem fingerprint completo em {path!r}")
        if not isinstance(item.get("sha256"), str) or not item.get("sha256"):
            raise SanitizeError(f"plano sem identidade de conteúdo em {path!r}")


def apply_plan(
    workspace: Path,
    *,
    plan: dict,
    today: date | None = None,
    rules: list[str] | None = None,
) -> dict:
    """Executa EXATAMENTE o plano aprovado.

    Re-detecta fresco (mesmos thresholds do plano) e compara item a item por
    fingerprint (regra, path, ação, tamanho, mtime, sha256): aprovado e
    idêntico → executa; aprovado mas alterado → `blocked`; aprovado que
    sumiu → `blocked`; detectado agora mas fora do plano → `blocked` (nunca
    entra de carona). `rules` filtra o plano aprovado, nunca o expande.
    """
    workspace = workspace.expanduser().resolve()
    _validate_plan(workspace, plan)
    t = Thresholds(**plan.get("thresholds", {}))
    fresh = build_plan(workspace, today=today, thresholds=t, rules=None)

    if rules is not None:
        wanted_rules = {rule for rule in rules if rule}
        if not wanted_rules:
            raise SanitizeError("seleção de regras vazia — nomeie as regras ou omita `--rules`")
        unknown = wanted_rules - set(RULES)
        if unknown:
            raise SanitizeError(f"regra desconhecida: {sorted(unknown)} (válidas: {', '.join(RULES)})")
    else:
        wanted_rules = None

    approved: dict[str, dict] = {}
    for item in plan.get("items", []):
        if wanted_rules is not None and item.get("rule") not in wanted_rules:
            continue
        approved[item["path"]] = item

    report = {**fresh, "mode": "apply"}
    executable: list[dict] = []
    blocked: list[dict] = []
    fresh_paths = set()
    for item in fresh["items"]:
        fresh_paths.add(item["path"])
        approved_item = approved.get(item["path"])
        if approved_item is None:
            if wanted_rules is None or item.get("rule") in wanted_rules:
                blocked.append(
                    {"path": item["path"], "reason": "não estava no plano aprovado — re-rode o dry-run"}
                )
            continue
        if _fingerprint(approved_item) != _fingerprint(item):
            blocked.append(
                {"path": item["path"], "reason": "mudou desde o plano aprovado — re-rode o dry-run"}
            )
            continue
        executable.append(item)
    for path, item in approved.items():
        if path not in fresh_paths:
            src = workspace / path
            if src.exists() or src.is_symlink():
                blocked.append({
                    "path": path,
                    "reason": "não é mais elegível — mudou ou ganhou symlink na árvore "
                    "desde o plano; re-rode o dry-run",
                })
            else:
                blocked.append({"path": path, "reason": "sumiu desde o plano"})

    report["items"] = executable

    # Rastro: valida índice E cercas de saída ANTES de qualquer mutação;
    # journal write-ahead no stamp.
    archive_payload, archive_md = _preflight_archive(workspace)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S-%f")
    backup_root = workspace / ".prumo" / "backups" / "sanitize" / stamp
    journal_path = backup_root / "SANITIZE-JOURNAL.json"
    if executable:
        _require_clean_write_target(workspace, backup_root, "backup do sanitize")
        _require_clean_write_target(
            workspace, workspace / ".prumo" / "backups" / "legacy" / stamp, "backup legacy"
        )
        backup_root.mkdir(parents=True, exist_ok=False)
        _atomic_write_text(
            journal_path,
            json.dumps(
                {
                    "schema_version": "prumo_sanitize_journal.v1",
                    "started_at": datetime.now().isoformat(timespec="seconds"),
                    "planned": executable,
                    "results": None,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )

    moved: list[str] = []
    deleted: list[str] = []
    index_entries: list[dict] = []
    now_iso = datetime.now().isoformat(timespec="seconds")

    for item in executable:
        source = workspace / item["path"]
        if not source.exists() and not source.is_symlink():
            blocked.append({"path": item["path"], "reason": "sumiu desde o plano"})
            continue
        if not _within_scope(workspace, source):
            blocked.append(
                {"path": item["path"], "reason": "fora do escopo `.prumo`/`_state` (symlink na cadeia?)"}
            )
            continue
        # Revalidação na FRONTEIRA da mutação: identidade recomputada agora
        # (não a da redetecção) e árvore livre de symlink — mudança
        # concorrente entre a checagem e a operação vira blocked.
        if source.is_symlink() or _tree_has_symlink(source):
            blocked.append(
                {"path": item["path"], "reason": "symlink surgiu na árvore desde o plano — bloqueado"}
            )
            continue
        identity_now = (
            _size_bytes(source),
            _mtime_ns(source),
            _content_id(workspace, source),
        )
        if identity_now != (item["size_bytes"], item["mtime_ns"], item["sha256"]):
            blocked.append(
                {"path": item["path"], "reason": "mudou na hora da execução — re-rode o dry-run"}
            )
            continue

        if item["action"] in {"move-to-backup", "consolidate"}:
            if item["action"] == "move-to-backup":
                target = backup_root / item["path"].replace("/", "__")
            else:
                target = workspace / ".prumo" / "backups" / "legacy" / stamp / source.name
            if target.exists() or target.is_symlink():
                blocked.append(
                    {"path": item["path"], "reason": f"destino de backup já existe ({target.name}) — colisão"}
                )
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            destino = _rel(workspace, target)
            moved.append(f"{item['path']} -> {destino}")
            index_entries.append(
                {"at": now_iso, "op": f"sanitize:{item['rule']}", "from": item["path"], "to": destino, "bytes": item["size_bytes"]}
            )
        else:  # delete
            if source.is_symlink():
                blocked.append(
                    {"path": item["path"], "reason": "symlink nunca é candidato — bloqueado"}
                )
                continue
            if source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()
            deleted.append(item["path"])
            entry = {"at": now_iso, "op": f"sanitize:{item['rule']}", "from": item["path"], "to": None, "bytes": item["size_bytes"]}
            if item.get("sha256"):
                entry["sha256"] = item["sha256"]
            index_entries.append(entry)

    # Legado singular esvaziado sai de cena (contrato do sanitize.md).
    legacy_root = workspace / ".prumo" / "backup"
    if legacy_root.is_dir() and not legacy_root.is_symlink() and not any(legacy_root.iterdir()):
        legacy_root.rmdir()

    if index_entries:
        _append_archive_index(
            workspace, index_entries, payload=archive_payload, md_text=archive_md
        )
    if executable:
        _atomic_write_text(
            journal_path,
            json.dumps(
                {
                    "schema_version": "prumo_sanitize_journal.v1",
                    "started_at": now_iso,
                    "planned": executable,
                    "results": {"moved": moved, "deleted": deleted, "blocked": blocked},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )

    report["apply"] = {
        "backup_root": _rel(workspace, backup_root) if backup_root.exists() else None,
        "moved": moved,
        "deleted": deleted,
        "blocked": blocked,
        "archive_index_updated": bool(index_entries),
    }
    return report
