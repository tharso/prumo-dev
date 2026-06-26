from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.fim import accumulation_signals


def _render_text(result: dict) -> str:
    s = result["signals"]
    lines = [
        f"1. Encerramento do workspace `{result['workspace_path']}`.",
        f"2. Pauta parada (>14d): {s['pauta_stalled']} · inbox pendente: {s['inbox_pending']} · registro: {s['registro_rows']} linhas.",
        f"3. Infra: backups velhos (>90d): {s['backups_old']} · HTMLs efêmeros velhos (>14d): {s['ephemeral_html_old']}.",
    ]
    sug = result["suggest"]
    if sug["higiene"] or sug["sanitize"]:
        propostas = []
        if sug["higiene"]:
            propostas.append("`/higiene` (conteúdo parado)")
        if sug["sanitize"]:
            propostas.append("`/sanitize` (infra acumulada)")
        lines.append(f"4. Acúmulo detectado — vale propor: {', '.join(propostas)}.")
    else:
        lines.append("4. Sem acúmulo relevante. Workspace limpo pra próxima sessão.")
    return "\n".join(lines)


def run_fim(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    result = accumulation_signals(workspace)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(_render_text(result))
    return 0
