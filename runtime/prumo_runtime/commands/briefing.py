from __future__ import annotations

from pathlib import Path

from prumo_runtime.workspace import (
    build_config_from_existing,
    extract_section,
    parse_core_version,
    read_text,
    semantic_version_key,
    update_briefing_state,
)
from prumo_runtime.constants import RUNTIME_VERSION


def list_or_placeholder(items: list[str], fallback: str) -> str:
    if not items:
        return fallback
    return "; ".join(items[:3])


def count_inbox_items(inbox_text: str) -> int:
    count = 0
    for line in inbox_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("- ", "* ")):
            count += 1
        elif stripped[:2].isdigit() and stripped[2:4] == ". ":
            count += 1
    return count


def run_briefing(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    config = build_config_from_existing(workspace)
    update_briefing_state(workspace, config.timezone_name)

    pauta_text = read_text(workspace / "PAUTA.md")
    inbox_text = read_text(workspace / "INBOX.md")
    quente = extract_section(pauta_text, "Quente (precisa de atenção agora)")
    andamento = extract_section(pauta_text, "Em andamento")
    agendado = extract_section(pauta_text, "Agendado / Lembretes")
    inbox_count = count_inbox_items(inbox_text)
    inbox_clean = "_Inbox limpo._" in inbox_text or inbox_count == 0
    core_version = parse_core_version(workspace)
    core_outdated = bool(core_version and semantic_version_key(core_version) < semantic_version_key(RUNTIME_VERSION))

    lines: list[str] = []
    n = 1

    if core_outdated:
        lines.append(
            f"{n}. Preflight: o runtime está em {RUNTIME_VERSION}, mas o core do workspace está em {core_version}. "
            "Não é tragédia nuclear, mas é drift e merece atenção."
        )
    else:
        lines.append(f"{n}. Preflight: runtime e workspace parecem minimamente alinhados.")
    n += 1

    lines.append(f"{n}. Quente: {len(quente)} item(ns). {list_or_placeholder(quente, 'Nada pegando fogo agora.')}")
    n += 1

    lines.append(
        f"{n}. Em andamento: {len(andamento)} item(ns). "
        f"{list_or_placeholder(andamento, 'Sem tração registrada no momento.')}"
    )
    n += 1

    lines.append(
        f"{n}. Agendado: {len(agendado)} item(ns). "
        f"{list_or_placeholder(agendado, 'Nenhum lembrete gritando por data neste instante.')}"
    )
    n += 1

    inbox_summary = "Inbox limpa." if inbox_clean else f"Inbox com {inbox_count} item(ns) pendente(s)."
    lines.append(f"{n}. Inbox: {inbox_summary}")
    n += 1

    if quente:
        proposal = quente[0]
    elif agendado:
        proposal = agendado[0]
    elif andamento:
        proposal = andamento[0]
    else:
        proposal = "Fazer um dump real de pendências antes que o sistema vire paisagem."

    lines.append(f"{n}. Proposta do dia: atacar primeiro `{proposal}`.")
    lines.append("a) ver a pauta detalhada")
    lines.append("b) seguir com a proposta do dia")
    lines.append("c) rodar repair se algo parecer fora do lugar")
    print("\n".join(lines))
    return 0
