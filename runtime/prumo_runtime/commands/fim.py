from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.fim import accumulation_signals


def _render_text(result: dict) -> str:
    s = result["signals"]
    lines = [
        f"1. Encerramento do workspace `{result['workspace_path']}`.",
        f"2. Pauta parada (>14d): {s['pauta_stalled']} · inbox pendente: {s['inbox_pending']} · registro: {s['registro_rows']} linhas.",
        f"3. Infra: backups velhos (>90d): {s['backups_old']} · artefatos efêmeros velhos (>14d): {s['ephemeral_old']}.",
    ]
    sug = result["suggest"]
    if sug["higiene"] or sug["sanitize"]:
        # Em linguagem de gente (#175): o comando é o COMO (a skill decide a
        # copy final); aqui nomeamos só o quê.
        propostas = []
        if sug["higiene"]:
            propostas.append("revisar conteúdo parado (higiene)")
        if sug["sanitize"]:
            propostas.append("limpar infra acumulada (sanitização técnica)")
        lines.append(f"4. Acúmulo detectado — vale propor: {', '.join(propostas)}.")
    else:
        lines.append("4. Sem acúmulo relevante. Workspace limpo pra próxima sessão.")
    if sug.get("update"):
        lines.append(
            f"5. Update pendente: {s['installed_version']} → {s['remote_version']} — "
            "vale oferecer antes de fechar (prumo update)."
        )
    return "\n".join(lines)


def run_fim(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    result = accumulation_signals(workspace)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(_render_text(result))
    return 0
