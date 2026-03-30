from __future__ import annotations

from pathlib import Path

from prumo_runtime import __version__
from prumo_runtime.workspace_paths import workspace_paths

RUNTIME_VERSION = __version__
SCHEMA_VERSION = "1.0"
ADAPTER_CONTRACT_VERSION = "2026-03-28"
DEFAULT_AGENT_NAME = "Prumo"
DEFAULT_TIMEZONE = "America/Sao_Paulo"
DEFAULT_BRIEFING_TIME = "09:00"

GENERATED_FILES = ("AGENT.md", "CLAUDE.md", "AGENTS.md", "PRUMO-CORE.md")
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
    "Referencias/WORKFLOWS.md",
)
DERIVED_FILES = (
    "_state/workspace-schema.json",
    "_state/briefing-state.json",
    "_state/google-integration.json",
    "Inbox4Mobile/_processed.json",
)
DIRECTORIES = ("Agente", "Inbox4Mobile", "Referencias", "_logs", "_state")


def generated_files_for(workspace: Path) -> tuple[str, ...]:
    return workspace_paths(workspace).generated_relative_paths()


def authorial_files_for(workspace: Path) -> tuple[str, ...]:
    return workspace_paths(workspace).authorial_relative_paths()


def derived_files_for(workspace: Path) -> tuple[str, ...]:
    return workspace_paths(workspace).derived_relative_paths()


def directories_for(workspace: Path) -> tuple[str, ...]:
    paths = workspace_paths(workspace)
    return tuple(paths.relative(directory) for directory in paths.directories())


def repo_root_from(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "VERSION").exists() and (candidate / "cowork-plugin").exists():
            return candidate
    return None


def canonical_refs_from(start: Path) -> dict[str, str]:
    repo_root = repo_root_from(start)
    if repo_root is None:
        return {}
    return {
        "canon_root": str(repo_root / "canon"),
        "invocation_contract": str(repo_root / "canon" / "contracts" / "invocation.md"),
        "interaction_contract": str(repo_root / "canon" / "contracts" / "interaction-format.md"),
        "file_governance": str(repo_root / "canon" / "governance" / "file-governance.md"),
        "load_policy": str(repo_root / "canon" / "governance" / "load-policy.md"),
        "briefing_orchestration": str(repo_root / "canon" / "orchestration" / "briefing.md"),
        "inbox_processing": str(repo_root / "canon" / "operations" / "inbox-processing.md"),
        "host_boundaries": str(repo_root / "canon" / "adapters" / "host-boundaries.md"),
    }
