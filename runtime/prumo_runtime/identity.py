"""Resolução de identidade do usuário a partir do workspace.

Cadeia canônica (Fase 2 da #97): schema → `Prumo/AGENT.md` → `Agente/INDEX.md`
legado (compat). Extraído de `workspace.py` para isolar a responsabilidade de
identidade e manter aquele módulo sob o teto de tamanho do quality gate.
"""

from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.workspace_paths import workspace_paths


def _read_schema(workspace: Path) -> dict:
    path = workspace_paths(workspace).workspace_schema
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parse_prefixed_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            value = stripped.split(":", 1)[1].strip()
            if value:
                return value
    return None


def _infer_user_name_from_agent(workspace: Path) -> str | None:
    agent_path = workspace_paths(workspace).canonical_agent
    if not agent_path.exists():
        return None
    return _parse_prefixed_value(
        agent_path.read_text(encoding="utf-8"), "- Nome preferido do usuário:"
    )


def _infer_user_name_from_legacy_index(workspace: Path) -> str | None:
    index_path = workspace_paths(workspace).agent_index
    if not index_path.exists():
        return None
    return _parse_prefixed_value(index_path.read_text(encoding="utf-8"), "- Nome preferido:")


def infer_user_name(workspace: Path) -> str | None:
    """Resolve a identidade do usuário: schema → AGENT.md → INDEX legado.

    O `AGENT.md` é a fonte canônica (Fase 2 da #97); o `INDEX.md` permanece
    só como fallback de compatibilidade para workspaces antigos.
    """
    schema = _read_schema(workspace)
    if schema.get("user_name"):
        return str(schema["user_name"])
    from_agent = _infer_user_name_from_agent(workspace)
    if from_agent:
        return from_agent
    return _infer_user_name_from_legacy_index(workspace)


def infer_user_name_from_legacy_claude(workspace: Path) -> str | None:
    claude_path = workspace_paths(workspace).wrappers["CLAUDE.md"]
    if not claude_path.exists():
        return None
    text = claude_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("- nome preferido:"):
            return stripped.split(":", 1)[1].strip()
        if stripped.lower().startswith("nome preferido:"):
            return stripped.split(":", 1)[1].strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# Prumo") and "—" in stripped:
            candidate = stripped.split("—", 1)[1].strip()
            if candidate:
                return candidate
    return None
