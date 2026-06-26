"""Enumerador read-only do "limbo" do Prumo para a skill `acervo`.

Lê três fontes DURÁVEIS e normaliza num JSON com proveniência por item
(path + âncora + linhas + hash), para revisão e remoção segura:

- `IDEIAS.md` — ideias soltas sem próxima ação (fragmentos)
- seção `## Hibernando` da `PAUTA.md` (fragmentos)
- arquivos de `Referencias/`, exceto os operacionais (arquivos inteiros)

Read-only: nunca escreve. A skill consome este JSON para montar o HTML e
para executar decisões. Decisão: DECISIONS.md 2026-06-26 (#125). Mantém a
#104 — enumerar markdown local é parsing determinístico, não curadoria de
email/agenda (que motivou barrar o runtime na geração da `decidir`).
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

from prumo_runtime.pauta_parsing import _section_header_matches
from prumo_runtime.workspace import read_text
from prumo_runtime.workspace_paths import WorkspacePaths, workspace_paths

SCHEMA_VERSION = "1.0"

# Contrato de campos de cada item — fonte única de verdade entre o enumerador
# (runtime), o fallback Markdown (skill) e o template HTML. Os testes cruzam
# este conjunto contra o template pra travar drift (Codex, rodada 2).
ITEM_FIELDS = (
    "item_id",
    "source_kind",
    "source_path",
    "anchor",
    "line_start",
    "line_end",
    "content_hash",
    "title",
    "snippet",
    "age_days",
    "tags",
)

HIBERNANDO_HEADING = "Hibernando"

# Arquivos operacionais de `Referencias/` que NUNCA entram no acervo: não são
# "limbo", são config viva (índice, regras de curadoria de email, workflows).
# Alinhado a `skills/prumo/references/file-protection-rules.md` e ao que a
# `faxina` já ignora ao catalogar. Ver DECISIONS.md 2026-06-26 (#125).
OPERATIONAL_REFERENCIAS = frozenset({"INDICE.md", "EMAIL-CURADORIA.md", "WORKFLOWS.md"})

# Só lê conteúdo (para título/snippet/hash de fragmento) de arquivos de texto.
# Outros formatos (pdf, imagens) entram como item de arquivo inteiro, hash dos
# bytes.
_TEXT_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".text"})

_TAG_PATTERN = re.compile(r"\[([^\[\]]+)\]")
_DESDE_PATTERN = re.compile(
    r"desde\s+(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{2,4}))?",
    re.IGNORECASE,
)

_TITLE_MAX = 90
_SNIPPET_MAX = 280


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _hash_text(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()[:16]


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def fragment_content_hash(lines_slice: list[str]) -> str:
    """Hash NORMALIZADO do trecho (linhas do arquivo, com whitespace colapsado).

    Fonte única usada pelo enumerador e pela remoção segura: recomputar o mesmo
    hash a partir das linhas atuais, imediatamente antes de cortar, prova que o
    conteúdo do trecho não mudou. `_normalize` colapsa whitespace — então funciona
    com ou sem `keepends`, mas NÃO detecta mudança só de espaços/quebras (essa é
    uma escolha: reformatação trivial não deve bloquear a remoção).
    """
    return _hash_text("".join(lines_slice))


def safe_items_json(items: list[dict], *, indent: int = 2) -> str:
    """Serializa os itens pra injeção segura num bloco `<script>` do template.

    Escapa `<`/`>`/`&` (e, via `ensure_ascii`, U+2028/U+2029) — sem isso, um
    título/snippet contendo `</script>` fecharia a tag e viraria XSS no
    documento que o usuário abre. Ver DECISIONS.md 2026-06-26 (#125).
    """
    raw = json.dumps(items, ensure_ascii=True, indent=indent)
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _truncate(text: str, limit: int) -> str:
    text = _normalize(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _extract_tags(text: str) -> list[str]:
    return [t.strip() for t in _TAG_PATTERN.findall(text) if t.strip()]


def _age_from_desde(text: str, today: date) -> int | None:
    match = _DESDE_PATTERN.search(text)
    if not match:
        return None
    day = int(match.group("day"))
    month = int(match.group("month"))
    year_raw = match.group("year")
    year = today.year if year_raw is None else (int(year_raw) + 2000 if int(year_raw) < 100 else int(year_raw))
    try:
        marked = date(year, month, day)
    except ValueError:
        return None
    if year_raw is None and marked > today:
        # "desde 30/12" lido em janeiro: era o ano passado.
        try:
            marked = date(year - 1, month, day)
        except ValueError:
            return None
    return max((today - marked).days, 0)


def _section_line_span(lines: list[str], heading: str) -> tuple[int, int] | None:
    """Intervalo [start, end) de linhas (0-based) do corpo de uma seção `## H`.

    Retorna None se a seção não existir. `start` é a primeira linha após o
    header; `end` é a próxima `## ` (ou o fim do arquivo).
    """
    marker = f"## {heading}"
    start: int | None = None
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            if start is not None:
                return (start, idx)
            if _section_header_matches(line.strip(), marker):
                start = idx + 1
    if start is None:
        return None
    return (start, len(lines))


def _iter_bullets(lines: list[str], offset: int, limit: int):
    """Itera itens de lista (bullets top-level) no intervalo [offset, limit).

    Um item é um bullet `- `/`* ` sem indentação, mais as linhas indentadas
    (continuação/sub-bullets) que o seguem. Rende dicts com `line_start`,
    `line_end` (1-based, inclusivo), `raw` (texto do item) e `section`.
    """
    current: dict | None = None
    section = ""
    for idx in range(offset, min(limit, len(lines))):
        line = lines[idx]
        stripped = line.strip()
        leading_space = line[:1].isspace()
        is_bullet = stripped[:2] in ("- ", "* ")

        if line.startswith("#"):
            if current is not None:
                yield current
                current = None
            section = line.lstrip("#").strip()
            continue

        if is_bullet and not leading_space:
            if current is not None:
                yield current
            content = stripped[2:].strip()
            current = {
                "line_start": idx + 1,
                "line_end": idx + 1,
                "raw_lines": [content],
                "section": section,
            }
        elif current is not None:
            if not stripped:
                yield current
                current = None
            elif leading_space:
                current["raw_lines"].append(stripped.lstrip("-* ").strip())
                current["line_end"] = idx + 1
            else:
                yield current
                current = None
    if current is not None:
        yield current


def _fragment_item(
    item_id: str, source_kind: str, source_path: str, bullet: dict, lines: list[str], today: date
) -> dict:
    raw = " ".join(p for p in bullet["raw_lines"] if p).strip()
    return {
        "item_id": item_id,
        "source_kind": source_kind,
        "source_path": source_path,
        "anchor": bullet.get("section") or None,
        "line_start": bullet["line_start"],
        "line_end": bullet["line_end"],
        # Hash normalizado do trecho (linhas do arquivo): a remoção segura
        # recomputa o mesmo hash a partir das linhas atuais antes de cortar.
        "content_hash": fragment_content_hash(lines[bullet["line_start"] - 1 : bullet["line_end"]]),
        "title": _truncate(raw, _TITLE_MAX),
        "snippet": _truncate(raw, _SNIPPET_MAX),
        "age_days": _age_from_desde(raw, today),
        "tags": _extract_tags(raw),
    }


def _enumerate_ideias(paths: WorkspacePaths, counter, today: date) -> list[dict]:
    text = read_text(paths.ideias)
    if not text:
        return []
    lines = text.splitlines()
    rel = paths.relative(paths.ideias)
    items = []
    for bullet in _iter_bullets(lines, 0, len(lines)):
        items.append(_fragment_item(next(counter), "ideia", rel, bullet, lines, today))
    return items


def _enumerate_hibernando(paths: WorkspacePaths, counter, today: date) -> list[dict]:
    text = read_text(paths.pauta)
    if not text:
        return []
    lines = text.splitlines()
    span = _section_line_span(lines, HIBERNANDO_HEADING)
    if span is None:
        return []
    rel = paths.relative(paths.pauta)
    items = []
    for bullet in _iter_bullets(lines, span[0], span[1]):
        bullet["section"] = HIBERNANDO_HEADING
        items.append(_fragment_item(next(counter), "pauta_hibernando", rel, bullet, lines, today))
    return items


def _first_heading_or_name(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return _truncate(stripped.lstrip("#").strip() or fallback, _TITLE_MAX)
        if stripped:
            return _truncate(stripped, _TITLE_MAX)
    return fallback


def _snippet_from_text(text: str, fallback: str) -> str:
    chunks = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return _truncate(" ".join(chunks), _SNIPPET_MAX) if chunks else fallback


def _enumerate_referencias(paths: WorkspacePaths, counter, today: date) -> list[dict]:
    root = paths.referencias_root
    if not root.exists():
        return []
    items = []
    for path in sorted(p for p in root.iterdir() if p.is_file()):
        name = path.name
        if name in OPERATIONAL_REFERENCIAS or name.startswith((".", "_")):
            continue
        is_text = path.suffix.lower() in _TEXT_SUFFIXES
        text = read_text(path) if is_text else ""
        try:
            content_hash = _hash_text(text) if is_text else _hash_bytes(path.read_bytes())
            age_days = max((today - date.fromtimestamp(path.stat().st_mtime)).days, 0)
        except OSError:
            continue
        items.append(
            {
                "item_id": next(counter),
                "source_kind": "referencia",
                "source_path": paths.relative(path),
                "anchor": name,
                "line_start": None,
                "line_end": None,
                "content_hash": content_hash,
                "title": _first_heading_or_name(text, name) if is_text else name,
                "snippet": _snippet_from_text(text, name) if is_text else name,
                "age_days": age_days,
                "tags": [],
            }
        )
    return items


def _id_counter():
    n = 0
    while True:
        n += 1
        yield f"acervo-{n}"


def enumerate_limbo(workspace: Path, *, today: date | None = None) -> dict:
    """Enumera o limbo durável do workspace. Read-only.

    Retorna `{schema_version, workspace_path, count, items}`. Cada item carrega
    proveniência (`source_kind`, `source_path`, `anchor`, `line_start`,
    `line_end`, `content_hash`) além de `title`, `snippet`, `age_days`, `tags`.
    """
    today = today or date.today()
    workspace = workspace.expanduser().resolve()
    paths = workspace_paths(workspace)
    counter = _id_counter()

    items: list[dict] = []
    items += _enumerate_ideias(paths, counter, today)
    items += _enumerate_hibernando(paths, counter, today)
    items += _enumerate_referencias(paths, counter, today)

    return {
        "schema_version": SCHEMA_VERSION,
        "workspace_path": str(workspace),
        "count": len(items),
        "items": items,
    }
