"""Manual de comandos do `/menu` (#130) — read-only.

Deriva a lista de comandos da **fonte canônica única**: a tabela "Comandos
disponíveis" do PRUMO-CORE.md do workspace. Sem segunda cópia da lista — se um
comando entra/sai do core, o `/menu` acompanha sozinho. A skill `menu` consome
isto pra apresentar o manual e abrir conversa ("tem dúvida?").

O parser vive em `command_table.py` (módulo folha) desde a #178 — o `/menu`
re-exporta `parse_command_table` pra compatibilidade de import.

Read-only: nunca escreve. Ver DECISIONS.md / issue #130.
"""
from __future__ import annotations

from pathlib import Path

from prumo_runtime.command_table import parse_command_table
from prumo_runtime.workspace import read_text
from prumo_runtime.workspace_paths import workspace_paths

__all__ = ["SCHEMA_VERSION", "command_manual", "parse_command_table"]

SCHEMA_VERSION = "1.0"


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
