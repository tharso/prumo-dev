"""Manual de comandos do `/menu` (#130) — read-only.

Deriva a lista de comandos da **fonte canônica única**: a tabela "Comandos
disponíveis" do PRUMO-CORE.md do workspace. Sem segunda cópia da lista — se um
comando entra/sai do core, o `/menu` acompanha sozinho. A skill `menu` consome
isto pra apresentar o manual e abrir conversa ("tem dúvida?").

Read-only: nunca escreve. Ver DECISIONS.md / issue #130.
"""
from __future__ import annotations

import re
from pathlib import Path

from prumo_runtime.workspace import read_text
from prumo_runtime.workspace_paths import workspace_paths

SCHEMA_VERSION = "1.0"

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


def command_manual(workspace: Path) -> dict:
    """Lê o PRUMO-CORE.md do workspace e devolve o manual de comandos. Read-only."""
    workspace = workspace.expanduser().resolve()
    core_path = workspace_paths(workspace).core
    commands = parse_command_table(read_text(core_path))
    return {
        "schema_version": SCHEMA_VERSION,
        "workspace_path": str(workspace),
        "source": str(core_path),
        "count": len(commands),
        "commands": commands,
    }
