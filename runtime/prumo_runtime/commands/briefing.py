from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.constants import RUNTIME_VERSION, repo_root_from
from prumo_runtime.constants import ADAPTER_CONTRACT_VERSION, canonical_refs_from
from prumo_runtime.daily_operator import (
    build_daily_actions,
    daily_operation_payload,
    next_move_payload,
    render_action_menu_lines,
    selection_contract_payload,
)
from prumo_runtime.inbox_preview import load_inbox_preview, summarize_inbox_entry
from prumo_runtime.workspace import (
    build_config_from_existing,
    extract_section,
    filter_by_due_date,
    load_json,
    migrate_briefing_state_to_last_briefing,
    parse_core_version,
    read_text,
    semantic_version_key,
    update_last_briefing,
    workspace_overview,
)
from prumo_runtime.workspace_paths import workspace_paths


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



def same_local_day(value: str | None, timezone_name: str) -> bool:
    if not value:
        return False
    try:
        dt_value = datetime.fromisoformat(value)
    except ValueError:
        return False
    now = datetime.now(ZoneInfo(timezone_name))
    return dt_value.astimezone(ZoneInfo(timezone_name)).date() == now.date()




def build_inbox_line(workspace: Path, inbox_text: str, preview: dict) -> str:
    inbox_count = count_inbox_items(inbox_text)
    preview_count = int(preview.get("count") or 0)
    preview_path = preview.get("preview_path")
    preview_hint = ""
    if isinstance(preview_path, Path) and preview_path.exists():
        preview_hint = f" Preview: `{preview_path}`."

    if preview_count == 0 and (preview.get("status") in {"gerado", "stale"}):
        note = preview.get("note") or "Inbox4Mobile sem itens novos."
        return f"Inbox4Mobile: 0 item(ns). {note}{preview_hint}".strip()

    if preview_count == 0:
        if inbox_count == 0 or "_Inbox limpo._" in inbox_text:
            return "Inbox4Mobile: 0 item(ns). Inbox limpa."
        return f"INBOX.md acusa {inbox_count} item(ns), mas o preview local não trouxe vitrine.{preview_hint}"

    top_items = [summarize_inbox_entry(item, workspace) for item in preview.get("items", [])[:3]]
    summary = "; ".join(top_items) if top_items else "há item, mas sem resumo leve decente."
    note = f" {preview.get('note')}" if preview.get("note") else ""
    return f"Inbox4Mobile: {preview_count} item(ns). {summary}.{note}{preview_hint}"


def build_briefing_degradation(
    *,
    core_outdated: bool,
    next_move: dict[str, object] | None,
) -> dict[str, object]:
    alerts: list[dict[str, object]] = []
    if core_outdated:
        alerts.append(
            {
                "id": "core-outdated",
                "level": "warning",
                "summary": "O core do workspace está defasado em relação ao runtime.",
                "action_id": "align-core",
            }
        )

    status = "ok"
    if any(alert["level"] == "error" for alert in alerts):
        status = "error"
    elif alerts:
        status = "partial"

    return {
        "status": status,
        "alerts": alerts,
    }


def choose_proposal(quente: list[str], agendado: list[str], andamento: list[str]) -> str:
    if quente:
        return quente[0]
    if agendado:
        return agendado[0]
    if andamento:
        return andamento[0]
    return "Fazer um dump real de pendências antes que o sistema vire paisagem."


def build_briefing_payload(workspace: Path, refresh_snapshot: bool = False) -> dict:
    workspace = workspace.expanduser().resolve()
    config = build_config_from_existing(workspace)
    repo_root = repo_root_from(Path(__file__))
    overview = workspace_overview(workspace)

    paths = workspace_paths(workspace)
    pauta_text = read_text(paths.pauta)
    inbox_text = read_text(paths.inbox)
    today = datetime.now(ZoneInfo(config.timezone_name)).date()
    quente = filter_by_due_date(extract_section(pauta_text, "Quente"), today)
    andamento = filter_by_due_date(extract_section(pauta_text, "Em andamento"), today)
    agendado = filter_by_due_date(extract_section(pauta_text, "Agendado"), today)

    preview = load_inbox_preview(workspace, repo_root)

    migrate_briefing_state_to_last_briefing(workspace)
    update_last_briefing(workspace, config.timezone_name)
    last_briefing_state = load_json(paths.last_briefing)
    last_briefing_at = str(last_briefing_state.get("at") or "").strip()
    has_briefed_today = same_local_day(last_briefing_at, config.timezone_name)

    core_version = parse_core_version(workspace)
    core_outdated = bool(core_version and semantic_version_key(core_version) < semantic_version_key(RUNTIME_VERSION))

    preflight_text = (
        f"o runtime está em {RUNTIME_VERSION}, mas o core do workspace está em {core_version}. "
        "Não é tragédia nuclear, mas é drift e merece atenção."
        if core_outdated
        else "runtime e workspace parecem minimamente alinhados."
    )
    inbox_mobile_text = build_inbox_line(workspace, inbox_text, preview)

    pauta_counts = {
        "quente": len(quente),
        "em_andamento": len(andamento),
        "agendado": len(agendado),
    }
    hottest = list_or_placeholder(quente or andamento or agendado, "Pauta sem tração aparente.")
    panorama_text = (
        f"Quente {pauta_counts['quente']} | Em andamento {pauta_counts['em_andamento']} | "
        f"Agendado {pauta_counts['agendado']}. {hottest}"
    )
    actions = build_daily_actions(workspace, overview, has_briefed_today=has_briefed_today)
    next_move = next_move_payload(actions)
    proposal = choose_proposal(quente, agendado, andamento)
    daily_operation = daily_operation_payload(workspace)
    degradation = build_briefing_degradation(
        core_outdated=core_outdated,
        next_move=next_move,
    )

    sections = [
        {"id": "preflight", "label": "Preflight", "text": preflight_text},
        {"id": "inbox_mobile", "label": "Inbox mobile", "text": inbox_mobile_text},
        {"id": "panorama_local", "label": "Panorama local", "text": panorama_text},
        {
            "id": "proposta_do_dia",
            "label": "Proposta do dia",
            "text": (
                f"seguir por `{next_move['label']}`."
                if next_move
                else f"atacar primeiro `{proposal}`."
            ),
        },
        {
            "id": "operacao_do_dia",
            "label": "Operação do dia",
            "text": (
                "O briefing é só a porta. O trabalho de verdade é continuar, organizar e registrar "
                "o que muda no workspace sem transformar o host em comentarista de si mesmo."
            ),
        },
    ]

    lines: list[str] = []
    for index, section in enumerate(sections, start=1):
        lines.append(f"{index}. {section['label']}: {section['text']}")
    if next_move:
        lines.append(f"{len(sections) + 1}. Próximo movimento recomendado: {next_move['label']}")
        lines.append(f"   `{next_move['command']}`")
        if next_move.get("why_now"):
            lines.append(f"   Motivo: {next_move['why_now']}")
        lines.append(
            "   Resposta curta aceita: `1`, `a` ou `aceitar` deve executar esse próximo movimento sem reabrir menu."
        )
    lines.extend(render_action_menu_lines(actions, next_move, workspace))

    return {
        "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
        "workspace_path": str(workspace),
        "runtime_version": RUNTIME_VERSION,
        "core_version": core_version or "",
        "core_outdated": core_outdated,
        "platform": overview["platform"],
        "capabilities": overview["capabilities"],
        "daily_operation": daily_operation,
        "next_move": next_move,
        "selection_contract": selection_contract_payload(next_move),
        "last_briefing_at": last_briefing_at,
        "actions": actions,
        "sections": sections,
        "proposal": {
            "text": proposal,
            "next_move": next_move,
            "options": [
                {
                    "id": action["id"],
                    "label": action["label"],
                    "kind": action["kind"],
                    "command": action["command"],
                }
                for action in actions[:4]
            ],
        },
        "degradation": degradation,
        "canonical_refs": canonical_refs_from(Path(__file__)),
        "message": "\n".join(lines),
    }


def run_briefing(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    payload = build_briefing_payload(
        workspace,
        refresh_snapshot=bool(getattr(args, "refresh_snapshot", False)),
    )
    if getattr(args, "format", "text") == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["message"])
    return 0
