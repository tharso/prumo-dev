from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.workspace import workspace_overview


def render_markdown(payload: dict) -> str:
    lines = [
        "# Prumo context-dump",
        "",
        f"- Workspace: `{payload['workspace_path']}`",
        f"- Usuário: `{payload['user_name']}`",
        f"- Agente: `{payload['agent_name']}`",
        f"- Runtime: `{payload['runtime_version']}`",
        f"- Core do workspace: `{payload['core_version'] or 'ausente'}`",
        f"- Schema: `{payload['schema_version']}`",
        f"- Core defasado: `{'sim' if payload['core_outdated'] else 'nao'}`",
        "",
        "## Missing",
        "",
        f"- generated: {', '.join(payload['missing']['generated']) or 'nenhum'}",
        f"- authorial: {', '.join(payload['missing']['authorial']) or 'nenhum'}",
        f"- derived: {', '.join(payload['missing']['derived']) or 'nenhum'}",
    ]
    return "\n".join(lines) + "\n"


def run_context_dump(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    payload = workspace_overview(workspace)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(render_markdown(payload), end="")
    return 0
