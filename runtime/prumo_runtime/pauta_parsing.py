"""Parsing de seções de markdown e do marker `| cobrar:` da PAUTA.

Extraído de `workspace.py` (#114, follow-up da Fatia 5) — eram utilitários
puros (texto/data) sem acoplamento com schema/render/repair, e o arquivo de
origem estava no teto do baseline de tamanho do quality gate.
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta

# Mantém o nome do logger do `workspace` de propósito: consumidores e testes
# filtram os warnings de `cobrar` por "prumo_runtime.workspace". Preservar o
# nome evita mudança de comportamento observável ao mover as funções.
_logger = logging.getLogger("prumo_runtime.workspace")

_SECTION_HEADER_SEPARATORS = frozenset("—-():|/")


def _section_header_matches(header_text: str, marker: str) -> bool:
    """Match de header tolerante a sufixo visual sem engolir seções parecidas.

    Casa "## Quente", "## Quente — Quarta 22/04" e "## Quente (precisa...)"
    para heading="Quente", mas NÃO casa "## Agendado Futuro" para heading="Agendado"
    porque a letra 'F' de 'Futuro' não é um separador visual reconhecido.
    """
    if header_text == marker:
        return True
    if not header_text.startswith(marker):
        return False
    tail = header_text[len(marker):].lstrip()
    if not tail:
        return True
    return tail[0] in _SECTION_HEADER_SEPARATORS


def extract_section(markdown: str, heading: str) -> list[str]:
    lines = markdown.splitlines()
    capture = False
    collected: list[str] = []
    marker = f"## {heading}"
    for line in lines:
        if line.startswith("## "):
            if capture:
                break
            capture = _section_header_matches(line.strip(), marker)
            continue
        if capture:
            stripped = line.strip()
            if not stripped or stripped.startswith("_"):
                continue
            collected.append(stripped)
    return collected


_COBRAR_MARKER_PATTERN = re.compile(r"\|\s*cobrar\s*:", re.IGNORECASE)
_COBRAR_DATE_PATTERN = re.compile(
    r"\|\s*cobrar\s*:\s*(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{2,4}))?",
    re.IGNORECASE,
)

_DUE_HORIZON_DAYS = 60
"""Heurística pro marker de ano implícito: se a data com ano atual caiu mais de
60 dias no passado, assumimos que o usuário quis dizer o ano seguinte."""


def parse_cobrar_date(item: str, today: date) -> date | None:
    """Extrai a data do marker `| cobrar: DD/MM[/AAAA]` de um item da pauta.

    Retorna None quando:
    - o item não tem o marker,
    - o marker existe mas está mal formado (loga warning).

    Ano implícito: se o marker é `DD/MM`, usa o ano de `today`. Se a data
    resultante já ficou muito no passado (mais de 60 dias), assumimos que o
    usuário quis o ano seguinte. Isso evita que "05/01" escrito em abril vire
    uma data 4 meses atrás — provavelmente o usuário quis dizer janeiro do
    próximo ano.
    """
    has_marker = bool(_COBRAR_MARKER_PATTERN.search(item))
    match = _COBRAR_DATE_PATTERN.search(item)
    if not match:
        if has_marker:
            _logger.warning(
                "marker cobrar mal formado no item %r (esperado DD/MM[/AAAA])",
                item,
            )
        return None

    day = int(match.group("day"))
    month = int(match.group("month"))
    year_raw = match.group("year")

    if year_raw is not None:
        year = int(year_raw)
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            _logger.warning(
                "marker cobrar inválido no item %r (data não existe)",
                item,
            )
            return None

    year = today.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        _logger.warning(
            "marker cobrar inválido no item %r (dia/mês não existe)",
            item,
        )
        return None

    if (today - candidate).days > _DUE_HORIZON_DAYS:
        try:
            candidate = date(year + 1, month, day)
        except ValueError:
            _logger.warning(
                "marker cobrar inválido no item %r (ano seguinte falhou)",
                item,
            )
            return None

    return candidate


def is_item_visible_today(item: str, today: date) -> bool:
    """Decide se um item da pauta deve aparecer no briefing do dia.

    Regra: item sem marker aparece sempre. Item com marker `cobrar: D` aparece
    quando falta no máximo 1 dia pra D (véspera ou dia). Itens atrasados (D no
    passado) continuam aparecendo — se o usuário não cuidou até a data, ele
    precisa ver o débito. Marker mal formado deixa o item visível (fail-open).
    """
    due = parse_cobrar_date(item, today)
    if due is None:
        return True
    return (due - today) <= timedelta(days=1)


def filter_by_due_date(items: list[str], today: date) -> list[str]:
    """Filtra uma lista de itens pelo marker `cobrar`, preservando a ordem."""
    return [item for item in items if is_item_visible_today(item, today)]
