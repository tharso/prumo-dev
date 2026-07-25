"""Índice de projetos com pulso determinístico puxado (#201).

Módulo folha. O `PROJETOS.md` do usuário é autoral-com-ilhas-gerenciadas:
dentro do contêiner `## Projetos registrados`, cada `### Nome` pode registrar
um `- Caminho:` e ganha um bloco `<!-- prumo:pulso:begin/end -->` que SÓ o
sync reescreve — todo o resto é preservado byte a byte. Zero LLM aqui: o
pulso vem de git/mtime; a narrativa (`.prumo-contexto.md` na raiz do projeto)
só contribui com o `updated:` do frontmatter. Conteúdo vindo dos projetos é
DADO (regra 18): sanitizado, incapaz de abrir/fechar blocos.

Design fechado com o Codex na issue #201 (2 rodadas): gramática estrita com
zero-escrita em erro estrutural, caminhos registrados delimitados
(materialização do escopo autorizado da #194), staleness que nunca declara
`fresh` sob dúvida (coleta incompleta, date-only no mesmo dia, narrativa
ausente → `indeterminate`).
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "prumo_projetos.v1"
PULSO_BEGIN = "<!-- prumo:pulso:begin -->"
PULSO_END = "<!-- prumo:pulso:end -->"
CONTAINER_HEADING = "## Projetos registrados"
CONTEXT_FILENAME = ".prumo-contexto.md"
PATH_FIELD = "- Caminho:"

GIT_TIMEOUT_SECONDS = 5.0
COMMITS_LIMIT = 5
SUBJECT_LIMIT = 80
SCAN_MAX_DEPTH = 2  # raiz = 0
SCAN_MAX_ENTRIES = 400
PORCELAIN_STAT_LIMIT = 50

# Mesmo espírito do perímetro (#194): pastas técnicas nunca contam atividade.
EXCLUDED_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "target",
    ".pytest_cache",
}

_GLOB_CHARS = set("*?[]")


@dataclass
class Entry:
    name: str
    path_raw: str | None
    header_line: int
    section_end: int  # exclusivo (linhas)
    block_inner_start: int | None = None  # linha após BEGIN
    block_inner_end: int | None = None  # linha do END


@dataclass
class ParseResult:
    entries: list[Entry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_projects_index(text: str) -> ParseResult:
    lines = text.splitlines()
    result = ParseResult()
    container_start = None
    for i, line in enumerate(lines):
        if line.strip() == CONTAINER_HEADING:
            container_start = i
            break
    if container_start is None:
        return result

    container_end = len(lines)
    for i in range(container_start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            container_end = i
            break

    current: Entry | None = None
    for i in range(container_start + 1, container_end):
        stripped = lines[i].strip()
        if stripped.startswith("### "):
            if current is not None:
                current.section_end = i
            current = Entry(name=stripped[4:].strip(), path_raw=None, header_line=i, section_end=container_end)
            result.entries.append(current)
            continue
        if current is None:
            if stripped in {PULSO_BEGIN, PULSO_END}:
                result.errors.append(f"linha {i + 1}: marcador de pulso fora de seção de projeto")
            continue
        if stripped.startswith(PATH_FIELD):
            if current.path_raw is not None:
                result.errors.append(f"projeto '{current.name}': mais de um `{PATH_FIELD}`")
            current.path_raw = stripped[len(PATH_FIELD):].strip()

    for entry in result.entries:
        begins = [
            i
            for i in range(entry.header_line, entry.section_end)
            if lines[i].strip() == PULSO_BEGIN
        ]
        ends = [
            i
            for i in range(entry.header_line, entry.section_end)
            if lines[i].strip() == PULSO_END
        ]
        if len(begins) > 1 or len(ends) > 1:
            result.errors.append(f"projeto '{entry.name}': marcadores de pulso duplicados")
            continue
        if len(begins) != len(ends):
            result.errors.append(f"projeto '{entry.name}': marcador de pulso órfão")
            continue
        if begins and ends[0] < begins[0]:
            result.errors.append(f"projeto '{entry.name}': marcadores de pulso invertidos")
            continue
        if begins:
            entry.block_inner_start = begins[0] + 1
            entry.block_inner_end = ends[0]

    names = [e.name for e in result.entries]
    for name in sorted({n for n in names if names.count(n) > 1}):
        result.errors.append(f"nome de projeto duplicado: '{name}'")
    paths = [e.path_raw for e in result.entries if e.path_raw]
    for raw in sorted({p for p in paths if paths.count(p) > 1}):
        result.errors.append(f"caminho registrado duplicado: '{raw}'")
    return result


def resolve_registered_path(
    raw: str, *, home: Path, workspace: Path
) -> tuple[Path | None, str | None]:
    raw = (raw or "").strip()
    if not raw:
        return None, "caminho vazio"
    if "$" in raw or _GLOB_CHARS & set(raw):
        return None, "caminho não pode conter glob ou variável"
    if not (raw.startswith("/") or raw.startswith("~")):
        return None, "caminho deve ser absoluto ou começar com ~"
    if raw.startswith("~"):
        if raw != "~" and not raw.startswith("~/"):
            return None, "~ só vale para o próprio home (~/...)"
        # Expansão contra o home INJETADO (não o do processo) — testável e
        # sem surpresa quando o runtime roda com HOME diferente.
        raw_path = home if raw == "~" else home / raw[2:]
    else:
        raw_path = Path(raw)
    resolved = raw_path.resolve(strict=False)
    home = home.resolve(strict=False)
    workspace = workspace.resolve(strict=False)
    for protected in (home, workspace):
        if protected == resolved or protected.is_relative_to(resolved):
            return None, f"caminho amplo demais (contém {protected.name or '/'})"
    return resolved, None


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None


def collect_git_pulse(path: Path, *, now: datetime) -> dict | None:
    if not (path / ".git").exists():
        return None
    pulse: dict = {
        "kind": "git",
        "branch": None,
        "dirty": False,
        "commits": [],
        "last_commit_at": None,
        "working_tree_activity_at": None,
        "last_activity_at": None,
        "complete": True,
        "errors": [],
    }

    branch = _run_git(path, "symbolic-ref", "--short", "HEAD")
    if branch is None:
        pulse["errors"].append("git indisponível ou timeout")
        pulse["complete"] = False
        return pulse
    pulse["branch"] = branch.stdout.strip() if branch.returncode == 0 else "(detached)"

    log = _run_git(path, "log", f"-{COMMITS_LIMIT}", "--format=%cI%x09%s")
    if log is not None and log.returncode == 0:
        for line in log.stdout.splitlines():
            when, _, subject = line.partition("\t")
            pulse["commits"].append({"date": when, "subject": subject})
        if pulse["commits"]:
            pulse["last_commit_at"] = pulse["commits"][0]["date"]

    porcelain = _run_git(path, "status", "--porcelain")
    if porcelain is None or porcelain.returncode != 0:
        pulse["errors"].append("git status falhou")
        pulse["complete"] = False
        return pulse
    entries = porcelain.stdout.splitlines()
    pulse["dirty"] = bool(entries)
    if entries:
        stats: list[float] = []
        if len(entries) > PORCELAIN_STAT_LIMIT:
            pulse["complete"] = False
        for line in entries[:PORCELAIN_STAT_LIMIT]:
            rel = line[3:]
            if " -> " in rel:
                rel = rel.split(" -> ", 1)[1]
            if rel.endswith("/"):
                # Diretório untracked colapsado: o mtime real está lá dentro
                # e não vamos varrer — coleta incompleta, nunca "fresh".
                pulse["complete"] = False
                continue
            try:
                stats.append(os.lstat(path / rel).st_mtime)
            except OSError:
                pulse["complete"] = False
        if stats:
            pulse["working_tree_activity_at"] = _iso(max(stats))

    candidates = [
        value
        for value in (pulse["last_commit_at"], pulse["working_tree_activity_at"])
        if value
    ]
    if candidates and pulse["complete"]:
        pulse["last_activity_at"] = max(candidates)
    return pulse


def collect_folder_pulse(
    path: Path, *, now: datetime, max_entries: int = SCAN_MAX_ENTRIES
) -> dict:
    pulse: dict = {
        "kind": "folder",
        "last_activity_at": None,
        "truncated": False,
        "complete": True,
        "errors": [],
    }
    latest: float | None = None
    visited = 0
    stack: list[tuple[Path, int]] = [(path, 0)]
    while stack:
        current, depth = stack.pop(0)
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            pulse["errors"].append(f"sem acesso: {current.name}")
            pulse["complete"] = False
            continue
        for child in children:
            if visited >= max_entries:
                pulse["truncated"] = True
                pulse["complete"] = False
                stack.clear()
                break
            visited += 1
            if child.is_symlink():
                continue  # jamais atravessar (perímetro, #194)
            if child.is_dir():
                if child.name in EXCLUDED_DIR_NAMES:
                    continue
                if depth + 1 <= SCAN_MAX_DEPTH:
                    stack.append((child, depth + 1))
                continue
            try:
                mtime = child.lstat().st_mtime
            except OSError:
                pulse["complete"] = False
                continue
            if latest is None or mtime > latest:
                latest = mtime
    if latest is not None:
        pulse["last_activity_at"] = _iso(latest)
    return pulse


_FRONTMATTER_UPDATED = re.compile(r"(?m)^updated:\s*(.+?)\s*$")


def read_narrative(project_path: Path) -> dict:
    ctx = project_path / CONTEXT_FILENAME
    narrative: dict = {
        "exists": False,
        "updated_at": None,
        "source": None,
        "date_only": False,
        "file_mtime": None,
    }
    if not ctx.exists():
        return narrative
    narrative["exists"] = True
    try:
        narrative["file_mtime"] = _iso(ctx.lstat().st_mtime)
        text = ctx.read_text(encoding="utf-8")
    except OSError:
        return narrative
    if not text.startswith("---"):
        return narrative
    closing = text.find("\n---", 3)
    if closing == -1:
        return narrative
    match = _FRONTMATTER_UPDATED.search(text[:closing])
    if not match:
        return narrative
    value = match.group(1)
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            date.fromisoformat(value)
            narrative["date_only"] = True
        else:
            datetime.fromisoformat(value)
    except ValueError:
        return narrative
    narrative["updated_at"] = value
    narrative["source"] = "frontmatter"
    return narrative


def _parse_when(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def compute_staleness(
    *,
    narrative_updated_at: str | None,
    last_activity_at: str | None,
    complete: bool,
    date_only: bool,
) -> str:
    if not narrative_updated_at or not complete or not last_activity_at:
        return "indeterminate"
    activity = _parse_when(last_activity_at)
    if activity is None:
        return "indeterminate"
    if date_only:
        narrative_day = date.fromisoformat(narrative_updated_at)
        if narrative_day == activity.date():
            # Date-only não distingue manhã de noite: nunca declarar fresh.
            return "indeterminate"
        return "fresh" if narrative_day > activity.date() else "stale"
    narrative = _parse_when(narrative_updated_at)
    if narrative is None:
        return "indeterminate"
    return "fresh" if narrative >= activity else "stale"


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def sanitize_text(value: str) -> str:
    """Conteúdo de projeto é DADO (regra 18): sem controles, sem poder de
    abrir/fechar comentários HTML (os marcadores dos blocos gerenciados)."""
    cleaned = _CONTROL_CHARS.sub("", value.replace("\n", " ").replace("\r", " "))
    return cleaned.replace("<!--", "<! --").replace("-->", "-- >")


def render_pulse_lines(pulse: dict, *, staleness: str, synced_at: str) -> list[str]:
    lines = [f"(pulso gerado por `prumo projetos --sync` em {synced_at} — não editar; frescor: {staleness})"]
    if pulse.get("error"):
        lines.append(f"- ERRO: {sanitize_text(pulse['error'])}")
        return lines
    if pulse["kind"] == "git":
        dirty = "sim" if pulse["dirty"] else "não"
        lines.append(f"- Git: branch `{sanitize_text(pulse['branch'] or '?')}` | mudanças não commitadas: {dirty}")
        if pulse["last_commit_at"]:
            lines.append(f"- Último commit: {pulse['last_commit_at']}")
        if pulse["working_tree_activity_at"]:
            lines.append(f"- Atividade não commitada: {pulse['working_tree_activity_at']}")
        for commit in pulse["commits"]:
            subject = sanitize_text(commit["subject"])[:SUBJECT_LIMIT]
            lines.append(f"  - {commit['date']} {subject}")
    else:
        activity = pulse["last_activity_at"] or "indeterminada"
        suffix = " (varredura truncada)" if pulse.get("truncated") else ""
        lines.append(f"- Pasta: última atividade {activity}{suffix}")
    narrative = pulse.get("narrative") or {}
    if narrative.get("updated_at"):
        lines.append(f"- Narrativa (`{CONTEXT_FILENAME}`): updated {narrative['updated_at']}")
    elif narrative.get("exists"):
        lines.append(f"- Narrativa (`{CONTEXT_FILENAME}`): sem `updated:` válido no frontmatter")
    else:
        lines.append(f"- Narrativa: sem `{CONTEXT_FILENAME}` no projeto")
    for err in pulse.get("errors", []):
        lines.append(f"- Aviso: {sanitize_text(err)}")
    return lines


def _collect_project(resolved: Path, *, now: datetime) -> dict:
    pulse = collect_git_pulse(resolved, now=now)
    if pulse is None:
        pulse = collect_folder_pulse(resolved, now=now)
    narrative = read_narrative(resolved)
    pulse["narrative"] = narrative
    pulse["staleness"] = compute_staleness(
        narrative_updated_at=narrative["updated_at"],
        last_activity_at=pulse.get("last_activity_at"),
        complete=bool(pulse.get("complete")),
        date_only=bool(narrative.get("date_only")),
    )
    return pulse


def sync_index_text(
    text: str, *, home: Path, workspace: Path, now: datetime
) -> tuple[str | None, dict]:
    """Sincroniza os blocos de pulso. Transacional: erro estrutural → (None, report)."""
    parsed = parse_projects_index(text)
    report: dict = {
        "schema_version": SCHEMA_VERSION,
        "synced_at": now.isoformat(),
        "structural": bool(parsed.errors),
        "errors": list(parsed.errors),
        "projects": [],
    }
    if parsed.errors:
        return None, report

    synced_at = now.date().isoformat()
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in text else "\n"
    replacements: list[tuple[Entry, list[str]]] = []
    for entry in parsed.entries:
        info: dict = {"name": entry.name, "path": entry.path_raw}
        if not entry.path_raw:
            info["note"] = "sem caminho registrado — pulso não coletado"
            report["projects"].append(info)
            continue
        resolved, err = resolve_registered_path(entry.path_raw, home=home, workspace=workspace)
        if err is None and not resolved.exists():
            err = "caminho registrado não existe"
        if err is not None:
            report["errors"].append(f"{entry.name}: {err}")
            info["error"] = err
            pulse = {"error": err, "kind": "erro"}
            info["staleness"] = "indeterminate"
        else:
            info["resolved_path"] = str(resolved)
            pulse = _collect_project(resolved, now=now)
            info["staleness"] = pulse["staleness"]
            info["kind"] = pulse["kind"]
            for err_item in pulse.get("errors", []):
                report["errors"].append(f"{entry.name}: {err_item}")
        report["projects"].append(info)
        body = [
            line + newline
            for line in render_pulse_lines(
                pulse, staleness=info.get("staleness", "indeterminate"), synced_at=synced_at
            )
        ]
        replacements.append((entry, body))

    for entry, body in sorted(replacements, key=lambda item: item[0].header_line, reverse=True):
        if entry.block_inner_start is not None:
            lines[entry.block_inner_start : entry.block_inner_end] = body
        else:
            insert_at = entry.section_end
            block = [PULSO_BEGIN + newline, *body, PULSO_END + newline]
            if insert_at > 0 and lines[insert_at - 1].strip() != "":
                block = [newline, *block]
            lines[insert_at:insert_at] = block
    return "".join(lines), report


def build_readonly_report(text: str, *, now: datetime) -> dict:
    parsed = parse_projects_index(text)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(),
        "structural": bool(parsed.errors),
        "errors": list(parsed.errors),
        "projects": [
            {
                "name": entry.name,
                "path": entry.path_raw,
                "has_pulse": entry.block_inner_start is not None,
            }
            for entry in parsed.entries
        ],
    }


def write_atomically(path: Path, content: str) -> None:
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".projetos-", suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
    finally:
        os.close(fd)
    Path(tmp_path).replace(path)
