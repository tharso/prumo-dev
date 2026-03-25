from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.daily_operator import (
    build_daily_actions,
    choose_continue_item,
    daily_operation_payload,
    inbox_item_count,
    next_move_payload,
    selection_contract_payload,
)
from prumo_runtime.workspace import (
    WorkspaceError,
    load_json,
    workspace_overview,
)

LEGACY_MARKERS = ("CLAUDE.md", "PRUMO-CORE.md", "PAUTA.md", "INBOX.md", "REGISTRO.md")
DEFAULT_DISCOVERY_DEPTH = 8
ADAPTER_CONTRACT_VERSION = "2026-03-21"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _same_local_day(value: str | None, timezone_name: str) -> bool:
    dt_value = _parse_iso(value)
    if dt_value is None:
        return False
    now = datetime.now(ZoneInfo(timezone_name))
    return dt_value.astimezone(ZoneInfo(timezone_name)).date() == now.date()


def _short_clock(value: str | None, timezone_name: str) -> str | None:
    dt_value = _parse_iso(value)
    if dt_value is None:
        return None
    return dt_value.astimezone(ZoneInfo(timezone_name)).strftime("%H:%M")


def _has_runtime_identity(workspace: Path) -> bool:
    return (workspace / "AGENT.md").exists() and (workspace / "_state" / "workspace-schema.json").exists()


def _looks_legacy(workspace: Path) -> bool:
    return (
        not _has_runtime_identity(workspace)
        and any((workspace / relative).exists() for relative in LEGACY_MARKERS)
    )


def _discover_workspace_from_cwd() -> Path:
    current = Path.cwd().resolve()
    for depth, candidate in enumerate((current, *current.parents)):
        if depth > DEFAULT_DISCOVERY_DEPTH:
            break
        if _has_runtime_identity(candidate) or _looks_legacy(candidate):
            return candidate
    return current


def _workspace_resolution_source(explicit_workspace: str | None, workspace: Path) -> str:
    if explicit_workspace:
        return "explicit"
    if workspace == Path.cwd().resolve():
        return "cwd"
    return "parent-discovery"


def _build_adapter_hints(workspace: Path) -> dict[str, object]:
    workspace_str = str(workspace)
    return {
        "contract_version": ADAPTER_CONTRACT_VERSION,
        "short_invocations": ["Prumo", "bom dia, Prumo"],
        "preferred_entrypoint": {
            "kind": "shell",
            "shell_command": "prumo",
        },
        "briefing_entrypoint": {
            "kind": "shell",
            "shell_command": f"prumo briefing --workspace {workspace_str} --refresh-snapshot",
        },
        "briefing_structured_entrypoint": {
            "kind": "shell",
            "shell_command": f"prumo briefing --workspace {workspace_str} --refresh-snapshot --format json",
        },
        "inbox_preview_entrypoint": {
            "kind": "shell",
            "shell_command": f"prumo inbox preview --workspace {workspace_str} --format json",
        },
        "structured_entrypoint": {
            "kind": "shell",
            "shell_command": f"prumo start --workspace {workspace_str} --format json",
        },
        "behavior": {
            "short_invocation": "run preferred_entrypoint",
            "explicit_briefing": "run briefing_entrypoint",
            "structured_briefing": "prefer briefing_structured_entrypoint when the host needs machine-readable briefing output",
            "inbox_preview": "use inbox_preview_entrypoint when triaging Inbox4Mobile or when the host needs the inbox preview instead of inventing it",
            "structured_actions": "prefer structured_entrypoint and obey actions[].kind",
            "short_acceptance": "if the user replies with 1, a, aceitar, aceitar e seguir, seguir or ok, execute next_move directly without rerunning start and without showing another menu first",
            "post_execution": "after executing an accepted or imperative action, report outcome and documentation changes before offering more options",
        },
    }


def _render_text_for_missing_workspace(workspace: Path) -> str:
    workspace_str = str(workspace)
    return "\n".join(
        [
            f"1. Não achei o workspace `{workspace_str}`.",
            "2. Então não faz sentido fingir briefing. Primeiro precisamos de chão.",
            "3. Minha sugestão: criar o workspace com `prumo setup`.",
            "a) Rodar `prumo setup --workspace "
            f"{workspace_str}`",
            "b) Escolher outro caminho de workspace",
        ]
    )


def _render_text_for_legacy_workspace(workspace: Path) -> str:
    workspace_str = str(workspace)
    return "\n".join(
        [
            f"1. Achei um workspace em `{workspace_str}`, mas ele ainda não tem identidade canônica do runtime.",
            "2. Em português simples: parece casa antiga. Não é caso de `setup`; é caso de `migrate`.",
            "3. Minha sugestão: adotar o workspace legado antes de pedir briefing.",
            f"a) Rodar `prumo migrate --workspace {workspace_str}`",
            f"b) Ver estado cru com `prumo context-dump --workspace {workspace_str} --format json`",
        ]
    )


def _render_text_for_unknown_directory(workspace: Path) -> str:
    workspace_str = str(workspace)
    return "\n".join(
        [
            f"1. `{workspace_str}` existe, mas não parece workspace do Prumo.",
            "2. Em português simples: aqui não há identidade canônica e também não há sinais fortes de workspace legado.",
            "3. Minha sugestão: se esta pasta era para ser o seu sistema, faça `setup`. Se o workspace mora em outro lugar, aponte o caminho sem charada.",
            f"a) Rodar `prumo setup --workspace {workspace_str}`",
            "b) Rodar `prumo start --workspace /caminho/do/workspace`",
        ]
    )


def _render_start_text(workspace: Path, overview: dict) -> str:
    timezone_name = overview["timezone"]
    missing = overview["missing"]
    google = overview["google_integration"]
    apple = overview["apple_reminders"]
    platform = overview["platform"]
    capabilities = overview["capabilities"]
    briefing_state = load_json(workspace / "_state" / "briefing-state.json")
    last_briefing_at = str(briefing_state.get("last_briefing_at") or "").strip()
    has_briefed_today = _same_local_day(last_briefing_at, timezone_name)
    last_briefing_clock = _short_clock(last_briefing_at, timezone_name)
    actions = build_daily_actions(workspace, overview, has_briefed_today=has_briefed_today)
    next_move = next_move_payload(actions)
    continue_item = choose_continue_item(workspace)
    inbox_count = inbox_item_count(workspace)
    workflow_registry = capabilities["workflow_scaffolding"]["registry_path"]

    if missing["generated"] or missing["derived"]:
        suggestion = "consertar a estrutura antes de brincar de produtividade."
    elif not has_briefed_today:
        suggestion = "rodar o briefing agora."
    elif continue_item:
        suggestion = "retomar a frente mais quente em vez de pedir outro mapa da cidade."
    elif inbox_count:
        suggestion = "processar a fila encostada antes que ela vire geologia."
    else:
        suggestion = "organizar o dia, atualizar a documentação viva e preparar bons candidatos a workflow em vez de ficar girando no vazio."

    lines = [
        f"1. {overview['user_name']}, o Prumo está de pé no workspace `{workspace}`.",
        (
            "2. Estado rápido: "
            f"Google `{google['active_profile_status']}`, "
            f"Apple Reminders `{apple['status']}`, "
            f"core `{overview['core_version'] or 'ausente'}`."
        ),
        (
            "3. Plataforma e escopo desta fase: "
            f"`{platform['label']}` com operador diário ligado, documentação viva em jogo "
            "e estrutura pronta para workflows."
        ),
    ]

    if missing["generated"] or missing["derived"] or missing["authorial"]:
        missing_parts: list[str] = []
        if missing["generated"] or missing["derived"]:
            missing_parts.append(
                f"faltam arquivos recriáveis ({len(missing['generated']) + len(missing['derived'])})"
            )
        if missing["authorial"]:
            missing_parts.append(f"faltam arquivos autorais ({len(missing['authorial'])})")
        lines.append("4. O workspace não está 100% inteiro: " + "; ".join(missing_parts) + ".")
        suggestion_index = 5
    else:
        if has_briefed_today and last_briefing_clock:
            lines.append(f"4. Você já passou pelo briefing hoje, às {last_briefing_clock}.")
        else:
            lines.append("4. Ainda não há briefing registrado hoje neste workspace.")
        suggestion_index = 5

    lines.append(
        "5. Valor mínimo esperado agora: briefing com qualidade, continuação de trabalho, "
        "organização do dia e documentação útil. Se o produto parar no panorama, virou GPS que não dirige."
    )
    suggestion_index = 6

    if not capabilities["providers"]["apple_reminders"]["supported"]:
        lines.append("6. Apple Reminders não existe nesta plataforma e, honestamente, não vai mandar nesta fase.")
        suggestion_index = 7
    elif apple["status"] != "connected":
        lines.append("6. Apple Reminders ficou fora do foco desta fase. Se estiver negado, tratamos como degradação aceitável, não como desculpa para o produto mancar.")
        suggestion_index = 7

    lines.append(f"{suggestion_index}. Minha sugestão: {suggestion}")
    if next_move:
        lines.append(f"{suggestion_index + 1}. Próximo movimento recomendado: {next_move['label']}")
        lines.append(f"   `{next_move['command']}`")
        if next_move.get("why_now"):
            lines.append(f"   Motivo: {next_move['why_now']}")
        suggestion_index += 1
    lines.append(
        f"{suggestion_index + 1}. Se aparecer padrão repetitivo de trabalho, registre o candidato em `{workflow_registry}`. Não force workflow de laboratório como se fosse contrato assinado."
    )
    lines.append(
        f"{suggestion_index + 2}. Resposta curta aceita: `1`, `a` ou `aceitar` deve executar o próximo movimento recomendado sem outro menu no meio."
    )
    option_labels = list("abcdefghi")
    for label, action in zip(option_labels, actions):
        lines.append(f"{label}) {action['label']}")
        lines.append(f"   `{action['command']}`")

    return "\n".join(lines)


def run_start(args) -> int:
    workspace = (
        Path(args.workspace).expanduser().resolve()
        if getattr(args, "workspace", None)
        else _discover_workspace_from_cwd()
    )
    if not workspace.exists():
        print(_render_text_for_missing_workspace(workspace))
        return 0
    if not workspace.is_dir():
        raise WorkspaceError(f"workspace não é diretório: {workspace}")

    try:
        overview = workspace_overview(workspace)
    except WorkspaceError:
        if _looks_legacy(workspace):
            print(_render_text_for_legacy_workspace(workspace))
            return 0
        if not getattr(args, "workspace", None):
            print(_render_text_for_unknown_directory(workspace))
            return 0
        raise

    has_briefed_today = _same_local_day(
        str(load_json(workspace / "_state" / "briefing-state.json").get("last_briefing_at") or "").strip(),
        overview["timezone"],
    )
    actions = build_daily_actions(
        workspace,
        overview,
        has_briefed_today=has_briefed_today,
    )
    next_move = next_move_payload(actions)

    payload = {
        "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
        "workspace_path": str(workspace),
        "workspace_resolution": {
            "source": _workspace_resolution_source(getattr(args, "workspace", None), workspace),
            "path": str(workspace),
        },
        "user_name": overview["user_name"],
        "runtime_version": overview["runtime_version"],
        "core_version": overview["core_version"],
        "platform": overview["platform"],
        "capabilities": overview["capabilities"],
        "daily_operation": daily_operation_payload(workspace),
        "next_move": next_move,
        "selection_contract": selection_contract_payload(next_move),
        "google_status": overview["google_integration"]["active_profile_status"],
        "apple_reminders_status": overview["apple_reminders"]["status"],
        "missing": overview["missing"],
        "adapter_hints": _build_adapter_hints(workspace),
        "actions": actions,
        "message": _render_start_text(workspace, overview),
    }

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    print(payload["message"])
    return 0
