"""Detector de acúmulo do `/fim` (#126) — read-only.

O `/fim` é a porta única de encerramento de sessão. Roda a `faxina` (automática)
e, quando detecta acúmulo que exige julgamento, **sugere** `/higiene` ou
`/sanitize` — nunca executa por conta própria (elas pedem aprovação). Este
módulo computa os sinais de acúmulo de forma determinística, usando os
thresholds PADRÃO da `faxina`/`sanitize` (overrides em `Prumo/Custom/rules/`
ainda não são lidos aqui — é só detecção pra sugerir, não execução).

Read-only: nunca escreve. NÃO lê email/calendário e NÃO toca `last-briefing.json`
(é encerramento, não briefing). Ver DECISIONS.md 2026-06-26 (#126).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from prumo_runtime.workspace import read_text
from prumo_runtime.workspace_paths import workspace_paths

SCHEMA_VERSION = "1.0"

# Thresholds reusados da faxina/sanitize (skills/faxina/references/thresholds.md).
PAUTA_STALLED_DAYS = 14   # item da pauta parado há mais de 14d → higiene
BACKUP_EXPIRY_DAYS = 90   # backup em .prumo/backups/ → sanitize
EPHEMERAL_HTML_DAYS = 14  # HTML efêmero do decidir/acervo → sanitize

_DESDE_PATTERN = re.compile(
    r"desde\s+(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{2,4}))?",
    re.IGNORECASE,
)
_BULLET = ("- ", "* ")
_DONE_CHECKBOX = re.compile(r"\[[xX]\]")  # GFM checkbox marcado (item concluído)


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _stalled_pauta_count(text: str, today: date) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped[:2] not in _BULLET:
            continue
        body = stripped[2:].lstrip()
        if _DONE_CHECKBOX.match(body):
            continue  # item concluído (GFM `- [x]`) não é acúmulo
        m = _DESDE_PATTERN.search(stripped)
        if not m:
            continue
        marked = _parse_desde(m, today)
        if marked is None:
            continue
        if (today - marked).days > PAUTA_STALLED_DAYS:
            count += 1
    return count


def _parse_desde(m: re.Match, today: date) -> date | None:
    """Resolve `desde DD/MM[/AAAA]`. Sem ano, retorna a ocorrência mais recente
    de DD/MM em ou antes de hoje — recuando anos quando preciso (ex.: `29/02`
    cai no ano bissexto anterior; `30/12` lido em janeiro cai no ano passado).
    """
    month, day = int(m.group("month")), int(m.group("day"))
    year_raw = m.group("year")
    if year_raw is not None:
        year = int(year_raw) + 2000 if int(year_raw) < 100 else int(year_raw)
        return _safe_date(year, month, day)
    for year in range(today.year, today.year - 5, -1):  # 5 anos cobre o ciclo bissexto
        cand = _safe_date(year, month, day)
        if cand is not None and cand <= today:
            return cand
    return None


def _inbox_pending_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip()[:2] in _BULLET)


def _registro_rows(text: str) -> int:
    rows = 0
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        if set(s) <= set("|-: "):  # linha separadora
            continue
        if re.search(r"\bData\b", s) and re.search(r"\bDestino\b", s):  # header
            continue
        rows += 1
    return rows


def _count_old_files(root: Path, today: date, max_age_days: int, suffix: str | None = None) -> int:
    if not root.exists():
        return 0
    count = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if suffix and path.suffix.lower() != suffix:
            continue
        try:
            age = (today - date.fromtimestamp(path.stat().st_mtime)).days
        except OSError:
            continue
        if age > max_age_days:
            count += 1
    return count


def accumulation_signals(workspace: Path, *, today: date | None = None) -> dict:
    """Computa os sinais de acúmulo do workspace. Read-only.

    Retorna sinais + `suggest` (quais limpezas assistidas vale propor). Não toca
    estado, não lê email/calendário, não marca briefing.
    """
    today = today or date.today()
    workspace = workspace.expanduser().resolve()
    paths = workspace_paths(workspace)

    pauta_stalled = _stalled_pauta_count(read_text(paths.pauta), today)
    inbox_pending = _inbox_pending_count(read_text(paths.inbox))
    registro_rows = _registro_rows(read_text(paths.registro))

    # A infra (backups, HTMLs efêmeros) vive sempre em `.prumo/` — hardcoded no
    # runtime (backup_root_for) e nas skills decidir/acervo —, independente do
    # layout flat/nested. Por isso olhamos `.prumo` direto, não `system_root`.
    dot = workspace / ".prumo"
    backups_old = (
        _count_old_files(dot / "backups", today, BACKUP_EXPIRY_DAYS)
        + _count_old_files(dot / "backup", today, BACKUP_EXPIRY_DAYS)  # legado
    )
    # Conta TODOS os arquivos velhos (não só .html): a sanitize também trata a
    # cópia da `Boliand.otf` como efêmera nesses diretórios.
    ephemeral_old = (
        _count_old_files(dot / "state" / "decidir", today, EPHEMERAL_HTML_DAYS)
        + _count_old_files(dot / "state" / "acervo", today, EPHEMERAL_HTML_DAYS)
    )

    suggest_higiene = pauta_stalled > 0 or inbox_pending > 0
    suggest_sanitize = backups_old > 0 or ephemeral_old > 0

    return {
        "schema_version": SCHEMA_VERSION,
        "workspace_path": str(workspace),
        "signals": {
            "pauta_stalled": pauta_stalled,
            "inbox_pending": inbox_pending,
            "registro_rows": registro_rows,
            "backups_old": backups_old,
            "ephemeral_old": ephemeral_old,
        },
        "suggest": {
            "higiene": suggest_higiene,
            "sanitize": suggest_sanitize,
        },
    }
