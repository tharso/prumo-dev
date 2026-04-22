from __future__ import annotations

import subprocess
import sys
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


def load_inbox_preview(workspace: Path, repo_root: Path | None) -> dict:
    paths = workspace_paths(workspace)
    inbox_dir = paths.inbox4mobile_root
    preview_path = inbox_dir / "inbox-preview.html"
    index_path = paths.inbox_preview_index
    processed = load_processed_filenames(workspace)
    preview_status = "ausente"
    preview_note = ""

    if inbox_dir.exists():
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

    payload = load_json(index_path)
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
    }
