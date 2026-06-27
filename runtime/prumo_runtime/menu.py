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
    """Extrai [{command, description}] da tabela "## Comandos disponíveis".

    Tolera o cabeçalho (`| Comando | Função |`) e a linha separadora (`|---|`).
    """
    commands: list[dict] = []
    in_section = False
    for line in core_text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_section = _SECTION in s
            continue
        if not in_section or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        cmd_cell, desc = cells[0], cells[1]
        if not cmd_cell or set(cmd_cell) <= set("-: "):  # separadora
            continue
        if cmd_cell.lower() == "comando":  # cabeçalho
            continue
        m = _BACKTICK.search(cmd_cell)
        command = m.group(1).strip() if m else cmd_cell
        commands.append({"command": command, "description": desc})
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
