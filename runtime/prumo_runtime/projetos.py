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

# Raízes multi-parte que a regra de profundidade não pega (ex.: /tmp resolve
# pra /private/tmp no macOS). Caminho EXATO aqui é amplo demais; descendentes
# específicos continuam registráveis.
_BROAD_ROOTS = {"/private/tmp", "/private/var", "/private/etc", "/usr/local"}


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
    container_lines = [i for i, line in enumerate(lines) if line.strip() == CONTAINER_HEADING]
    if len(container_lines) > 1:
        result.errors.append(f"contêiner `{CONTAINER_HEADING}` duplicado")
        return result
    container_start = container_lines[0] if container_lines else None
    if container_start is None:
        for i, line in enumerate(lines):
            if line.strip() in {PULSO_BEGIN, PULSO_END}:
                result.errors.append(
                    f"linha {i + 1}: marcador de pulso fora do contêiner `{CONTAINER_HEADING}`"
                )
        return result
    for i, line in enumerate(lines):
        if line.strip() in {PULSO_BEGIN, PULSO_END} and i < container_start:
            result.errors.append(
                f"linha {i + 1}: marcador de pulso fora do contêiner `{CONTAINER_HEADING}`"
            )

    container_end = len(lines)
    for i in range(container_start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            container_end = i
            break

    current: Entry | None = None
    for i in range(container_start + 1, container_end):
        stripped = lines[i].strip()
        if stripped.startswith("###") and not stripped.startswith("####"):
            if not re.match(r"###[ \t]+\S", stripped):
                result.errors.append(f"linha {i + 1}: seção de projeto malformada (use `### Nome`)")
                continue
            name = stripped[3:].strip()
            if current is not None:
                current.section_end = i
            current = Entry(name=name, path_raw=None, header_line=i, section_end=container_end)
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

    for i in range(container_end, len(lines)):
        if lines[i].strip() in {PULSO_BEGIN, PULSO_END}:
            result.errors.append(
                f"linha {i + 1}: marcador de pulso fora do contêiner `{CONTAINER_HEADING}`"
            )

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
    windows_abs = bool(re.match(r"^[A-Za-z]:[\\/]", raw))
    if not (raw.startswith("/") or raw.startswith("~") or windows_abs):
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
    if len(resolved.parts) <= 2 or str(resolved) in _BROAD_ROOTS:
        # "/", "/Volumes", "/tmp" (→ /private/tmp no macOS)... — raiz ampla
        # demais; só descendentes específicos podem ser registrados
        # (Codex, design r2 + diff r1).
        return None, "caminho amplo demais (raiz do sistema)"
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
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
        # OPTIONAL_LOCKS=0: `git status` não atualiza stat-cache/index — o
        # contrato do sync é escrever SOMENTE o PROJETOS.md (Codex r2).
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            env=env,
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
    if log is None:
        pulse["errors"].append("git log falhou (timeout)")
        pulse["complete"] = False
    elif log.returncode == 0:
        for line in log.stdout.splitlines():
            when, _, subject = line.partition("\t")
            # Sanitiza NA ORIGEM: o payload JSON expõe os commits e o
            # orçamento de 80 chars vale nos dois formatos (Codex r2).
            pulse["commits"].append(
                {"date": when, "subject": sanitize_text(subject)[:SUBJECT_LIMIT]}
            )
        if pulse["commits"]:
            pulse["last_commit_at"] = pulse["commits"][0]["date"]
    else:
        head = _run_git(path, "rev-parse", "--verify", "HEAD")
        if head is None:
            # Timeout aqui não pode virar "unborn" silencioso (Codex r3).
            pulse["errors"].append("git rev-parse falhou (timeout)")
            pulse["complete"] = False
        elif head.returncode == 0:
            # HEAD existe e o log falhou mesmo assim: erro real, não unborn.
            pulse["errors"].append("git log falhou")
            pulse["complete"] = False

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
            pulse["errors"].append("mudanças demais no working tree — coleta parcial")
        for line in entries[:PORCELAIN_STAT_LIMIT]:
            rel = line[3:]
            if " -> " in rel:
                rel = rel.split(" -> ", 1)[1]
            if rel.endswith("/"):
                # Diretório untracked colapsado: o mtime real está lá dentro
                # e não vamos varrer — coleta incompleta, nunca "fresh".
                pulse["complete"] = False
                if "diretório untracked não varrido — coleta parcial" not in pulse["errors"]:
                    pulse["errors"].append("diretório untracked não varrido — coleta parcial")
                continue
            try:
                st = os.lstat(path / rel)
                # chmod muda ctime sem tocar mtime: dirty por metadata
                # também é atividade (Codex r2) — usar o mais recente.
                stats.append(max(st.st_mtime, st.st_ctime))
            except OSError:
                pulse["complete"] = False
                pulse["errors"].append(f"sem stat em mudança do working tree: {rel}")
        if stats:
            pulse["working_tree_activity_at"] = _iso(max(stats))

    candidates = []
    for value in (pulse["last_commit_at"], pulse["working_tree_activity_at"]):
        parsed = _parse_when(value) if value else None
        if parsed is not None:
            candidates.append((parsed, value))
    if candidates and pulse["complete"]:
        # Máximo CRONOLÓGICO — max() lexical de ISO com offsets distintos
        # não é ordem temporal (Codex diff r1).
        pulse["last_activity_at"] = max(candidates, key=lambda c: c[0])[1]
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
                pulse["errors"].append("varredura truncada no cap — coleta parcial")
                stack.clear()
                break
            visited += 1
            if child.is_symlink():
                continue  # jamais atravessar (perímetro, #194)
            if child.is_dir():
                if child.name in EXCLUDED_DIR_NAMES:
                    continue
                if depth + 1 <= SCAN_MAX_DEPTH - 1:
                    # Enumerar conteúdo até depth == SCAN_MAX_DEPTH (raiz=0):
                    # dir em depth N só é aberto se seus filhos ficarem <= N.
                    stack.append((child, depth + 1))
                continue
            try:
                mtime = child.lstat().st_mtime
            except OSError:
                pulse["complete"] = False
                pulse["errors"].append(f"sem stat: {child.name}")
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
        "error": None,
    }
    if ctx.is_symlink():
        # Antes do exists(): link QUEBRADO tem exists()==False e viraria
        # "narrativa ausente" em silêncio (Codex r2).
        narrative["exists"] = True
        narrative["error"] = "contexto é symlink — ignorado"
        return narrative
    if not ctx.exists():
        return narrative
    narrative["exists"] = True
    try:
        narrative["file_mtime"] = _iso(ctx.lstat().st_mtime)
        text = ctx.read_bytes().decode("utf-8")
    except OSError:
        narrative["error"] = "contexto ilegível"
        return narrative
    except UnicodeDecodeError:
        narrative["error"] = "contexto com encoding inválido"
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
    # RFC 3339 COM offset — timestamp naive é rejeitado: um UTC inventado
    # compararia errado contra offsets reais (Codex diff r1).
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def compute_staleness(
    *,
    narrative_updated_at: str | None,
    last_activity_at: str | None,
    complete: bool,
    date_only: bool,
    now: datetime,
) -> str:
    if not narrative_updated_at or not complete or not last_activity_at:
        return "indeterminate"
    activity = _parse_when(last_activity_at)
    if activity is None:
        return "indeterminate"
    if date_only:
        narrative_day = date.fromisoformat(narrative_updated_at)
        if narrative_day > now.date():
            return "indeterminate"  # narrativa do futuro é relógio quebrado
        activity_day = activity.astimezone(timezone.utc).date()
        if narrative_day == activity_day:
            # Date-only não distingue manhã de noite: nunca declarar fresh.
            return "indeterminate"
        return "fresh" if narrative_day > activity_day else "stale"
    narrative = _parse_when(narrative_updated_at)
    if narrative is None:
        return "indeterminate"
    if narrative > now:
        return "indeterminate"  # futuro nunca é fresh (Codex reproduziu com 2099)
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
    if narrative.get("error"):
        pulse.setdefault("errors", []).append(f"narrativa: {narrative['error']}")
    pulse["staleness"] = compute_staleness(
        narrative_updated_at=narrative["updated_at"],
        last_activity_at=pulse.get("last_activity_at"),
        complete=bool(pulse.get("complete")),
        date_only=bool(narrative.get("date_only")),
        now=now,
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

    canonical_seen: dict[str, str] = {}
    resolutions: dict[int, tuple[Path | None, str | None]] = {}
    for entry in parsed.entries:
        if not entry.path_raw:
            continue
        resolved, err = resolve_registered_path(entry.path_raw, home=home, workspace=workspace)
        resolutions[entry.header_line] = (resolved, err)
        if resolved is None:
            continue
        key = str(resolved)
        if key in canonical_seen:
            report["errors"].append(
                f"caminho duplicado após canonicalização: '{entry.path_raw}' e "
                f"'{canonical_seen[key]}' apontam pra {key}"
            )
            report["structural"] = True
        else:
            canonical_seen[key] = entry.path_raw
    if report["structural"]:
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
            if entry.block_inner_start is not None:
                # Pulso antigo de um caminho removido continuaria mentindo
                # frescor (Codex r3) — o miolo vira nota explícita.
                replacements.append(
                    (entry, [f"(sem caminho registrado — pulso não coletado; {synced_at})" + newline])
                )
            continue
        # Canonicalizado UMA vez na pré-validação — reutilizar fecha a
        # janela de troca de alvo entre validação e coleta (Codex r2).
        resolved, err = resolutions[entry.header_line]
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
            for key in (
                "branch",
                "dirty",
                "last_commit_at",
                "working_tree_activity_at",
                "last_activity_at",
                "commits",
                "truncated",
                "complete",
            ):
                if key in pulse:
                    info[key] = pulse[key]
            narr = pulse.get("narrative") or {}
            info["narrative"] = {
                "exists": narr.get("exists", False),
                "updated_at": narr.get("updated_at"),
                "source": narr.get("source"),
                "file_mtime": narr.get("file_mtime"),
                "error": narr.get("error"),
            }
            info["errors"] = list(pulse.get("errors", []))
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

    needs_eof_insert = any(
        entry.block_inner_start is None and entry.section_end >= len(lines)
        for entry, _ in replacements
    )
    if needs_eof_insert and lines and not lines[-1].endswith(("\n", "\r\n")):
        # Sem newline final, um bloco inserido no EOF colaria o marcador na
        # última linha e o parse seguinte acusaria órfão (Codex r4/r5). Byte
        # estrutural aplicado SÓ neste caso — doc sem inserção fica intocado.
        lines[-1] += newline

    for entry, body in sorted(replacements, key=lambda item: item[0].header_line, reverse=True):
        if entry.block_inner_start is not None:
            lines[entry.block_inner_start : entry.block_inner_end] = body
        else:
            # Inserção estrita: SÓ os marcadores + miolo — nenhum byte
            # decorativo fora dos delimitadores (Codex r3).
            insert_at = entry.section_end
            block = [PULSO_BEGIN + newline, *body, PULSO_END + newline]
            lines[insert_at:insert_at] = block
    return "".join(lines), report


_PERSISTED_STALENESS = re.compile(r"frescor:\s*(fresh|stale|indeterminate)")
_PERSISTED_SYNCED_AT = re.compile(r"em\s+(\d{4}-\d{2}-\d{2})")


def build_readonly_report(text: str, *, now: datetime) -> dict:
    """Report SEM acesso externo: só o que está persistido no índice."""
    parsed = parse_projects_index(text)
    lines = text.splitlines()
    projects = []
    for entry in parsed.entries:
        info: dict = {
            "name": entry.name,
            "path": entry.path_raw,
            "has_pulse": entry.block_inner_start is not None,
            "staleness": None,
            "synced_at": None,
        }
        if entry.block_inner_start is not None:
            inner = "\n".join(lines[entry.block_inner_start : entry.block_inner_end])
            staleness = _PERSISTED_STALENESS.search(inner)
            synced = _PERSISTED_SYNCED_AT.search(inner)
            info["staleness"] = staleness.group(1) if staleness else None
            info["synced_at"] = synced.group(1) if synced else None
        projects.append(info)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(),
        "structural": bool(parsed.errors),
        "errors": list(parsed.errors),
        "projects": projects,
    }


def write_atomically(path: Path, content: str) -> None:
    """Escrita integral + replace atômico, preservando o mode do original
    (mkstemp cria 0600 — substituir um 0644 mudaria permissões; Codex r1)."""
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".projetos-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content.encode("utf-8"))
        if path.exists():
            os.chmod(tmp_path, path.stat().st_mode & 0o7777)
        Path(tmp_path).replace(path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
