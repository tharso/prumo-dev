from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.workspace import workspace_overview


def render_markdown(payload: dict) -> str:
    platform = payload["platform"]
    capabilities = payload["capabilities"]
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
        f"- Plataforma: `{platform['label']}` ({platform['system']} {platform['release']})",
        f"- Runtime app dir: `{platform['runtime_app_dir']}`",
        "",
        "## Capacidades",
        "",
        f"- operador diário: `{'sim' if capabilities['daily_operation']['continuation'] else 'nao'}`",
        f"- documentação viva: `{'sim' if capabilities['daily_operation']['documentation'] else 'nao'}`",
        f"- estrutura para workflows: `{capabilities['workflow_scaffolding']['delivery']}`",
        f"- registro de workflows: `{capabilities['workflow_scaffolding']['registry_path']}`",
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
