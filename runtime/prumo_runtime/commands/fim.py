from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.fim import accumulation_signals


def _tech_parts(s: dict) -> list[str]:
    # Só famílias com contagem > 0 entram na recomendação — citar "0 backups"
    # quando o gatilho foi outro sinal é contradição visível (#179 PR10).
    # .get() porque schema 1.0 não tinha os dois últimos (aditivo).
    parts = []
    if s["backups_old"]:
        parts.append(f"{s['backups_old']} backups")
    if s["ephemeral_old"]:
        parts.append(f"{s['ephemeral_old']} efêmeros")
    if s.get("handover_legacy", 0):
        parts.append(f"{s['handover_legacy']} arquivos de sessão aposentados")
    if s.get("nested_backups", 0):
        parts.append(f"{s['nested_backups']} backups aninhados")
    return parts


def _render_text(result: dict) -> str:
    s = result["signals"]
    lines = [
        f"1. Encerramento do workspace `{result['workspace_path']}`.",
        f"2. Pauta parada (>14d): {s['pauta_stalled']} · inbox pendente: {s['inbox_pending']} · registro: {s['registro_rows']} linhas.",
        f"3. Poeira técnica: backups velhos (>90d): {s['backups_old']} · arquivos efêmeros (>14d): {s['ephemeral_old']}"
        f" · handovers legados: {s.get('handover_legacy', 0)} · backups aninhados: {s.get('nested_backups', 0)}.",
    ]
    sug = result["suggest"]
    # UMA recomendação em linguagem de gente (#175): conteúdo > técnica; o
    # secundário vira cláusula, nunca segunda proposta. Comando nenhum aqui —
    # o comando é o COMO e mora na skill, depois do sim.
    tech = ", ".join(_tech_parts(s)) or "poeira técnica acumulada"
    if sug["higiene"]:
        rec = f"revisar o conteúdo parado ({s['pauta_stalled']} na pauta, {s['inbox_pending']} no inbox)"
        if sug["sanitize"]:
            rec += f" — e limpar a poeira técnica junto ({tech})"
        lines.append(f"4. Recomendação: {rec}.")
    elif sug["sanitize"]:
        lines.append(f"4. Recomendação: limpar a poeira técnica ({tech}).")
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
