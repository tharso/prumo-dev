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
        if (candidate / "VERSION").exists() and (candidate / "plugin.json").exists():
            return candidate
    return None


def canonical_refs_from(start: Path) -> dict[str, str]:
    """References to canonical module files (skills-first, all under skills/)."""
    repo_root = repo_root_from(start)
    if repo_root is None:
        return {}
    modules = repo_root / "skills" / "prumo" / "references" / "modules"
    return {
        "briefing_procedure": str(modules / "briefing-procedure.md"),
        "inbox_processing": str(modules / "inbox-processing.md"),
        "interaction_format": str(modules / "interaction-format.md"),
        "file_governance": str(modules / "runtime-file-governance.md"),
        "load_policy": str(modules / "load-policy.md"),
        "weekly_review": str(modules / "weekly-review.md"),
        "multiagent": str(modules / "multiagent.md"),
        "sanitization": str(modules / "sanitization.md"),
    }
