"""Parser da tabela canônica de comandos do PRUMO-CORE.md (#178, épico #177).

Módulo folha (só `re`): a tabela "## Comandos disponíveis" do core é a fonte
única da lista de comandos (#172). Este parser saiu de `menu.py` pra cá
porque `templates.py` também vai derivar dela (cadeia de fallback do
AGENT.md, M2 do #177) — e importar de `menu` criaria o ciclo
`templates ← workspace ← menu`.
"""

from __future__ import annotations

import re

_SECTION = "Comandos disponíveis"
_BACKTICK = re.compile(r"`([^`]+)`")


def parse_command_table(core_text: str) -> list[dict]:
    """Extrai [{command, description}] da PRIMEIRA tabela após "## Comandos
    disponíveis".

    Captura só a tabela contígua imediatamente seguinte ao heading — para no
    primeiro bloco não-tabela ou no próximo heading. Assim uma sub-tabela (ex.:
    `### Notas` dentro da seção) não vira comando. Tolera o cabeçalho
    (`| Comando | Função |`) e a separadora (`|---|`). Contrato: a descrição
    não pode conter `|` cru (é célula de tabela Markdown).
    """
    lines = core_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("## ") and _SECTION in s:
            start = i + 1
            break
    if start is None:
        return []

    commands: list[dict] = []
    started = False
    for line in lines[start:]:
        s = line.strip()
        if s.startswith("#"):  # próximo heading encerra a seção
            break
        if not s.startswith("|"):
            if started:
                break  # acabou a tabela contígua
            continue   # texto entre o heading e a tabela
        started = True
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        cmd_cell, desc = cells[0], cells[1]
        if not cmd_cell or set(cmd_cell) <= set("-: "):  # separadora
            continue
        if cmd_cell.lower() == "comando":  # cabeçalho
            continue
        m = _BACKTICK.search(cmd_cell)
        commands.append({"command": m.group(1).strip() if m else cmd_cell, "description": desc})
    return commands
