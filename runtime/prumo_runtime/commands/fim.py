from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.fim import accumulation_signals


def _render_text(result: dict) -> str:
    s = result["signals"]
    lines = [
        f"1. Encerramento do workspace `{result['workspace_path']}`.",
        f"2. Pauta parada (>14d): {s['pauta_stalled']} · inbox pendente: {s['inbox_pending']} · registro: {s['registro_rows']} linhas.",
        f"3. Poeira técnica: backups velhos (>90d): {s['backups_old']} · arquivos efêmeros (>14d): {s['ephemeral_old']}.",
    ]
    sug = result["suggest"]
    # UMA recomendação em linguagem de gente (#175): conteúdo > técnica; o
    # secundário vira cláusula, nunca segunda proposta. Comando nenhum aqui —
    # o comando é o COMO e mora na skill, depois do sim.
    if sug["higiene"]:
        rec = f"revisar o conteúdo parado ({s['pauta_stalled']} na pauta, {s['inbox_pending']} no inbox)"
        if sug["sanitize"]:
            rec += f" — e limpar a poeira técnica junto ({s['backups_old']} backups, {s['ephemeral_old']} efêmeros)"
        lines.append(f"4. Recomendação: {rec}.")
    elif sug["sanitize"]:
        lines.append(
            f"4. Recomendação: limpar a poeira técnica ({s['backups_old']} backups, {s['ephemeral_old']} efêmeros)."
        )
    else:
        lines.append("4. Sem acúmulo relevante. Workspace limpo pra próxima sessão.")
    if sug.get("update"):
        lines.append(
            f"5. Update pendente: {s['installed_version']} → {s['remote_version']} — oferecer antes de fechar."
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
