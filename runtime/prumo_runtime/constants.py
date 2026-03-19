from __future__ import annotations

from pathlib import Path

from prumo_runtime import __version__

RUNTIME_VERSION = __version__
SCHEMA_VERSION = "1.0"
DEFAULT_AGENT_NAME = "Prumo"
DEFAULT_TIMEZONE = "America/Sao_Paulo"
DEFAULT_BRIEFING_TIME = "09:00"

GENERATED_FILES = (
    "AGENT.md",
    "CLAUDE.md",
    "AGENTS.md",
    "PRUMO-CORE.md",
)

AUTHORIAL_FILES = (
    "Agente/INDEX.md",
    "Agente/PESSOAS.md",
    "Agente/SAUDE.md",
    "Agente/ROTINA.md",
    "Agente/INFRA.md",
    "Agente/PROJETOS.md",
    "Agente/RELACOES.md",
    "PAUTA.md",
    "INBOX.md",
    "REGISTRO.md",
    "IDEIAS.md",
    "Referencias/INDICE.md",
)

DERIVED_FILES = (
    "_state/workspace-schema.json",
    "_state/briefing-state.json",
    "Inbox4Mobile/_processed.json",
)

DIRECTORIES = (
    "Agente",
    "Inbox4Mobile",
    "Referencias",
    "_logs",
    "_state",
)


def repo_root_from(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "VERSION").exists() and (candidate / "cowork-plugin").exists():
            return candidate
    return None
