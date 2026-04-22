from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.constants import repo_root_from
from prumo_runtime.daily_operator import documentation_targets, daily_operation_payload
from prumo_runtime.inbox_preview import load_inbox_preview, summarize_inbox_entry
from prumo_runtime.workspace import workspace_overview


def _build_actions(workspace: Path) -> list[dict[str, object]]:
    docs = documentation_targets(workspace)
    inbox = docs["inbox"]
    pauta = docs["pauta"]
    registro = docs["registro"]
    workflow_registry = docs["workflow_registry"]
    return [
        {
            "id": "process-inbox",
            "kind": "host-prompt",
            "category": "inbox-triage",
            "label": "Triar a fila com preview na mesa",
            "command": (
                f"Processe a fila atual do workspace usando o preview do inbox como vitrine. "
                f"Triague `{inbox}`, atualize `{pauta}`, limpe o que for resolvido de `{inbox}` "
                f"e registre decisões em `{registro}` sem inventar contexto."
            ),
            "host_prompt": (
                f"Processe a fila atual do workspace usando o preview do inbox como vitrine. "
                f"Triague `{inbox}`, atualize `{pauta}`, limpe o que for resolvido de `{inbox}` "
                f"e registre decisões em `{registro}` sem inventar contexto."
            ),
            "documentation_targets": [pauta, inbox, registro],
            "outcome": "Fila menor, documentação mais clara e menos entulho virando geologia emocional.",
        },
        {
            "id": "workflow-scaffold",
            "kind": "host-prompt",
            "category": "workflow-scaffolding",
            "label": "Registrar padrões que merecem virar workflow depois",
            "command": (
                f"Revise os itens da fila e registre em `{workflow_registry}` padrões repetíveis, "
                "gatilhos e documentação necessária sem forçar workflow fechado agora."
            ),
            "host_prompt": (
                f"Revise os itens da fila e registre em `{workflow_registry}` padrões repetíveis, "
                "gatilhos e documentação necessária sem forçar workflow fechado agora."
            ),
            "documentation_targets": [workflow_registry, registro],
            "outcome": "Padrões registrados sem vender automação de PowerPoint como produto pronto.",
        },
        {
            "id": "context",
            "kind": "shell",
            "category": "diagnostics",
            "label": "Ver o estado técnico sem poesia",
            "command": f"prumo context-dump --workspace {workspace} --format json",
            "shell_command": f"prumo context-dump --workspace {workspace} --format json",
            "documentation_targets": [pauta, inbox, registro],
            "outcome": "Estado técnico explícito quando a conversa pedir bisturi em vez de metáfora.",
        },
    ]


def build_inbox_preview_payload(workspace: Path) -> dict[str, object]:
    workspace = workspace.expanduser().resolve()
    overview = workspace_overview(workspace)
    preview = load_inbox_preview(workspace, repo_root_from(Path(__file__)))
    docs = documentation_targets(workspace)
    samples = [summarize_inbox_entry(item, workspace) for item in preview["items"][:5]]
    note = str(preview.get("note") or "").strip()

    if preview["count"]:
        summary = "; ".join(samples[:3])
        message = (
            f"1. Inbox preview pronto em `{preview['preview_path']}`.\n"
            f"2. Há `{preview['count']}` item(ns) pendente(s) para triagem.\n"
            f"3. Amostra rápida: {summary}.\n"
            f"4. Isso não é briefing; é vitrine. O trabalho começa quando você decide o destino de cada coisa."
        )
    else:
        message = (
            f"1. Inbox preview pronto em `{preview['preview_path']}`.\n"
            "2. Não encontrei itens novos para triagem.\n"
            "3. Boa notícia rara: a fila parece limpa."
        )
    if note:
        message += f"\n4. Nota do preview: {note}"

    return {
        "workspace_path": str(workspace),
        "user_name": overview["user_name"],
        "runtime_version": overview["runtime_version"],
        "core_version": overview["core_version"],
        "platform": overview["platform"],
        "capabilities": overview["capabilities"],
        "daily_operation": daily_operation_payload(workspace),
        "documentation_targets": {
            "pauta": docs["pauta"],
            "inbox": docs["inbox"],
            "registro": docs["registro"],
            "workflow_registry": docs["workflow_registry"],
            "preview_html": str(preview["preview_path"]),
            "preview_index": str(preview["index_path"]),
        },
        "preview": {
            "status": preview["status"],
            "note": note,
            "count": preview["count"],
            "preview_path": str(preview["preview_path"]),
            "index_path": str(preview["index_path"]),
            "items": preview["items"],
            "sample": samples,
        },
        "actions": _build_actions(workspace),
        "message": message,
    }


def _render_text(payload: dict[str, object]) -> str:
    preview = payload["preview"]
    lines = [
        f"1. Inbox preview do workspace `{payload['workspace_path']}`.",
        f"2. Status do preview: `{preview['status']}`.",
        f"3. Itens pendentes para triagem: `{preview['count']}`.",
        f"4. HTML: `{preview['preview_path']}`.",
        f"5. Índice JSON: `{preview['index_path']}`.",
    ]
    note = str(preview.get("note") or "").strip()
    if note:
        lines.append(f"6. Nota: {note}")
    sample = preview.get("sample") or []
    if sample:
        lines.append("7. Amostra: " + "; ".join(sample[:3]))
    else:
        lines.append("7. Sem amostra porque a fila está vazia ou invisível.")
    lines.append(
        "8. Se quiser transformar vitrine em trabalho, siga pela triagem e registre destino em documentação viva."
    )
    return "\n".join(lines)


def run_inbox_preview(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    payload = build_inbox_preview_payload(workspace)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(_render_text(payload))
    return 0
