from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.menu import command_manual

PROACTIVE_QUESTION = "Tem alguma dúvida sobre como o Prumo funciona? É só perguntar."


def _render_text(result: dict) -> str:
    lines = ["Manual do Prumo — comandos disponíveis:", ""]
    if not result["commands"]:
        lines.append("(não encontrei a tabela de comandos no core do workspace)")
    for c in result["commands"]:
        lines.append(f"- `{c['command']}` — {c['description']}")
    lines.append("")
    lines.append(PROACTIVE_QUESTION)
    return "\n".join(lines)


def run_menu(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    result = command_manual(workspace)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(_render_text(result))
    return 0
