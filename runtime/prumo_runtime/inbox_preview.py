from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from prumo_runtime.workspace import load_json
from prumo_runtime.workspace_paths import workspace_paths


def find_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_processed_filenames(workspace: Path) -> set[str]:
    payload = load_json(workspace_paths(workspace).inbox_processed)
    items = payload.get("items", [])
    names: set[str] = set()
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            if isinstance(filename, str) and filename.strip():
                names.add(filename.strip())
    return names


def preview_script_path(repo_root: Path | None) -> Path | None:
    package_script = Path(__file__).with_name("generate_inbox_preview.py")
    candidates = [package_script]
    if repo_root is not None:
        candidates.extend(
            [
                repo_root / "scripts" / "generate_inbox_preview.py",
            ]
        )
    return find_existing_path(candidates)


def infer_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return None
    return host.replace("www.", "") or None


def summarize_text_preview(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1", errors="replace")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            if len(stripped) > 120:
                return stripped[:117] + "..."
            return stripped
    return path.name


def summarize_inbox_entry(entry: dict, workspace: Path | None = None) -> str:
    filename = str(entry.get("filename") or "item sem nome")
    kind = str(entry.get("kind") or "arquivo")
    relative_path = entry.get("relative_path")
    absolute_path = entry.get("absolute_path")  # legacy, pra compatibilidade
    first_url = entry.get("first_url")
    domain = infer_domain(first_url)

    if kind == "image":
        return f"{filename} (imagem/captura)"
    if kind == "pdf":
        return f"{filename} (PDF)"

    resolved_path: Path | None = None
    if kind == "text":
        if isinstance(relative_path, str) and workspace is not None:
            candidate = Path(relative_path)
            if not candidate.is_absolute():
                candidate = workspace / candidate
            resolved_path = candidate
        elif isinstance(absolute_path, str):
            resolved_path = Path(absolute_path)

    if kind == "text" and resolved_path is not None and resolved_path.exists():
        preview = summarize_text_preview(resolved_path)
        if domain:
            return f"{filename}: {preview} ({domain})"
        return f"{filename}: {preview}"
    if domain:
        return f"{filename} ({domain})"
    return filename


# Mobília operacional da vitrine — MESMO conjunto que `generate_inbox_preview`
# exclui (o gerador ignora `_processed.json` por nome e os outputs por path).
# Dotfile NÃO é exclusão: conteúdo real oculto conta como conteúdo.
_OPERATIONAL_NAMES = {"inbox-preview.html", "_preview-index.json", "_processed.json"}


def _scan_inbox_top_level(inbox_dir: Path) -> dict:
    """Snapshot ÚNICO do top-level do Inbox4Mobile (listagem plana e rasa —
    perímetro #194): {newest, count, error}. Conta ARQUIVOS de conteúdo pelo
    predicado canônico (exclui mobília operacional e symlinks; dotfile real
    conta). Falha de varredura vira `error` — nunca "vazio" de mentira."""
    result: dict = {"newest": None, "count": 0, "error": None}
    try:
        entries = list(inbox_dir.iterdir())
    except OSError as exc:
        result["error"] = f"varredura do Inbox4Mobile falhou: {exc}"
        return result
    import stat as stat_module

    for entry in entries:
        try:
            st = entry.lstat()  # UMA operação por entrada: classifica e data
        except OSError as exc:
            result["error"] = f"stat falhou em {entry.name}: {exc}"
            continue
        if stat_module.S_ISLNK(st.st_mode) or not stat_module.S_ISREG(st.st_mode):
            continue
        if entry.name in _OPERATIONAL_NAMES:
            continue
        result["count"] += 1
        result["newest"] = (
            st.st_mtime if result["newest"] is None else max(result["newest"], st.st_mtime)
        )
    return result


def load_inbox_preview(
    workspace: Path, repo_root: Path | None, *, allow_regen: bool = False
) -> dict:
    """Vitrine do Inbox4Mobile.

    Por default é SEMENTE READ-ONLY (#197): apenas lê o índice existente e
    reporta o status comparando mtimes — zero subprocesso, zero escrita. O
    enum COMPLETO de status é `gerado|stale|ausente|invalido|indeterminado`
    (`invalido`: índice symlinkado/ilegível/sem `items` válido;
    `indeterminado`: a varredura do diretório falhou). Qualquer status
    diferente de `gerado` significa fonte incompleta — o consumidor faz
    fallback por fonte. A regeneração (subprocesso de até 20s que reescreve
    preview+índice) só acontece com `allow_regen=True` — a operação explícita
    do `prumo inbox preview` — e NUNCA é acionada implicitamente pelo
    briefing; outputs symlinkados abortam ANTES do subprocesso.
    """
    paths = workspace_paths(workspace)
    inbox_dir = paths.inbox4mobile_root
    preview_path = inbox_dir / "inbox-preview.html"
    index_path = paths.inbox_preview_index

    # Root symlinkado (quebrado incluso — is_symlink() enxerga o que exists()
    # esconde): NENHUM acesso aos filhos. Nem _processed, nem varredura, nem
    # índice, nem subprocesso — recusar pra escrita e depois ler seria barrar
    # o caminhão e entrar nele pra conferir a carga.
    if inbox_dir.is_symlink():
        return {
            "status": "invalido",
            "note": "Inbox4Mobile é symlink — recusado; aponte o diretório real.",
            "preview_path": preview_path,
            "index_path": index_path,
            "count": 0,
            "items": [],
            "freshness": {"index_mtime": None, "newest_inbox_mtime": None},
            "raw_files_count": 0,
            "scan_error": "Inbox4Mobile é symlink",
            "index_present": False,
        }

    processed = load_processed_filenames(workspace)
    preview_status = "ausente"
    preview_note = ""

    # Preflight de symlink ANTES de qualquer subprocesso: regenerar com
    # outputs symlinkados escreveria através do link em alvo externo — o
    # leitor recusaria DEPOIS, mas aí o estrago já teria acontecido.
    regen_blocked = ""
    for candidate, label in (
        (inbox_dir, "Inbox4Mobile"),
        (preview_path, "inbox-preview.html"),
        (index_path, "_preview-index.json"),
    ):
        if candidate.is_symlink():
            regen_blocked = f"{label} é symlink — regeneração recusada."
            break

    if allow_regen and inbox_dir.exists() and regen_blocked:
        preview_status = "invalido"
        preview_note = regen_blocked
    elif allow_regen and inbox_dir.exists():
        script_path = preview_script_path(repo_root)
        if script_path is not None:
            try:
                subprocess.run(
                    [
                        sys.executable,
                        str(script_path),
                        "--inbox-dir",
                        str(inbox_dir),
                        "--output",
                        str(preview_path),
                        "--index-output",
                        str(index_path),
                    ],
                    cwd=str(workspace),
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                preview_status = "gerado"
            except Exception:
                if preview_path.exists() and index_path.exists():
                    preview_status = "stale"
                    preview_note = "preview reaproveitado; a regeneração falhou e o resultado pode estar defasado."
                else:
                    preview_status = "falhou"
                    preview_note = "preview indisponível; segui sem vitrine."
    # SNAPSHOT ÚNICO do diretório: status, frescor e contagem bruta saem da
    # MESMA varredura (duas passadas abririam janela pra estados divergentes).
    scan = (
        _scan_inbox_top_level(inbox_dir)
        if inbox_dir.exists()
        else {"newest": None, "count": 0, "error": None}
    )
    scan_error = scan["error"]
    raw_files_count = scan["count"]

    if not allow_regen and inbox_dir.exists():
        if scan_error is not None:
            preview_status = "indeterminado"
            preview_note = f"{scan_error} — frescor e contagem indeterminados."
        elif index_path.exists():
            try:
                index_mtime = index_path.stat().st_mtime
            except OSError:
                index_mtime = None
            if index_mtime is not None and (
                scan["newest"] is None or index_mtime >= scan["newest"]
            ):
                preview_status = "gerado"
            else:
                preview_status = "stale"
                preview_note = (
                    "índice do preview mais velho que o Inbox4Mobile; "
                    "rode `prumo inbox preview` pra regenerar."
                )

    freshness: dict[str, str | None] = {"index_mtime": None, "newest_inbox_mtime": None}
    if index_path.exists():
        try:
            freshness["index_mtime"] = datetime.fromtimestamp(
                index_path.stat().st_mtime, tz=timezone.utc
            ).isoformat(timespec="seconds")
        except OSError:
            pass
    if scan["newest"] is not None:
        freshness["newest_inbox_mtime"] = datetime.fromtimestamp(
            scan["newest"], tz=timezone.utc
        ).isoformat(timespec="seconds")

    # Índice presente mas symlinkado, ilegível ou estruturalmente inválido
    # (sem a chave `items` como lista de objetos) NÃO passa por "gerado" com
    # zero itens — vira status próprio e fonte incompleta.
    payload: dict = {}
    if index_path.is_symlink():
        preview_status = "invalido"
        preview_note = "índice do preview é symlink — recusado; rode `prumo inbox preview`."
    elif index_path.exists():
        try:
            loaded = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            loaded = None
        if (
            isinstance(loaded, dict)
            and isinstance(loaded.get("items"), list)
            and all(isinstance(item, dict) for item in loaded["items"])
        ):
            payload = loaded
        else:
            preview_status = "invalido"
            preview_note = "índice do preview ilegível — rode `prumo inbox preview` pra regenerar."
    raw_items = payload.get("items", [])
    items: list[dict] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            if isinstance(filename, str) and filename in processed:
                continue
            items.append(item)

    return {
        "status": preview_status,
        "note": preview_note,
        "preview_path": preview_path,
        "index_path": index_path,
        "count": len(items),
        "items": items,
        "freshness": freshness,
        "raw_files_count": raw_files_count,
        "scan_error": scan_error,
        "index_present": index_path.exists() or index_path.is_symlink(),
    }
