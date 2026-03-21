from __future__ import annotations

import json
import os
import string
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.workspace import (
    WorkspaceError,
    extract_section,
    load_json,
    read_text,
    workspace_overview,
)

LEGACY_MARKERS = ("CLAUDE.md", "PRUMO-CORE.md", "PAUTA.md", "INBOX.md", "REGISTRO.md")
DEFAULT_GOOGLE_CLIENT_SECRETS = Path("~/Documents/_secrets/prumo/google-oauth-client.json").expanduser()
DEFAULT_DISCOVERY_DEPTH = 8
ADAPTER_CONTRACT_VERSION = "2026-03-21"


def _shell_action(action_id: str, label: str, shell_command: str) -> dict[str, str]:
    return {
        "id": action_id,
        "label": label,
        "kind": "shell",
        "command": shell_command,
        "shell_command": shell_command,
    }


def _host_prompt_action(action_id: str, label: str, host_prompt: str) -> dict[str, str]:
    return {
        "id": action_id,
        "label": label,
        "kind": "host-prompt",
        "command": host_prompt,
        "host_prompt": host_prompt,
    }


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


def _pauta_candidates(workspace: Path) -> tuple[list[str], list[str]]:
    pauta = read_text(workspace / "PAUTA.md")
    hot = extract_section(pauta, "Quente (precisa de atenção agora)")
    ongoing = extract_section(pauta, "Em andamento")
    clean_hot = [item for item in hot if "_Nada ainda._" not in item and "Nada ainda." not in item]
    clean_ongoing = [item for item in ongoing if "_Nada ainda._" not in item and "Nada ainda." not in item]
    return clean_hot, clean_ongoing


def _clean_pauta_item(value: str | None) -> str:
    text = str(value or "").strip()
    if text.startswith("- "):
        text = text[2:].strip()
    return text


def _choose_continue_item(workspace: Path) -> str | None:
    hot, ongoing = _pauta_candidates(workspace)
    if hot:
        return hot[0]
    if ongoing:
        return ongoing[0]
    return None


def _suggest_google_auth_action(workspace: Path) -> dict[str, str]:
    workspace_str = str(workspace)
    client_secrets_env = str(os.environ.get("PRUMO_GOOGLE_CLIENT_SECRETS") or "").strip()
    client_id = str(os.environ.get("PRUMO_GOOGLE_CLIENT_ID") or "").strip()
    client_secret = str(os.environ.get("PRUMO_GOOGLE_CLIENT_SECRET") or "").strip()
    if client_secrets_env:
        candidate = Path(client_secrets_env).expanduser()
        if candidate.exists():
            return _shell_action(
                "auth-google",
                "Conectar Google",
                f"prumo auth google --workspace {workspace_str} --client-secrets {candidate}",
            )
    if DEFAULT_GOOGLE_CLIENT_SECRETS.exists():
        return _shell_action(
            "auth-google",
            "Conectar Google",
            f"prumo auth google --workspace {workspace_str} --client-secrets {DEFAULT_GOOGLE_CLIENT_SECRETS}",
        )
    if client_id and client_secret:
        return _shell_action(
            "auth-google",
            "Conectar Google",
            (
                f'prumo auth google --workspace {workspace_str} --client-id "{client_id}" '
                f'--client-secret "{client_secret}"'
            ),
        )
    return _shell_action(
        "auth-google-help",
        "Ver como conectar Google sem chute cego",
        f"prumo auth google --workspace {workspace_str} --help",
    )


def _build_actions(workspace: Path, overview: dict) -> list[dict[str, str]]:
    workspace_str = str(workspace)
    missing = overview["missing"]
    briefing_state = load_json(workspace / "_state" / "briefing-state.json")
    last_briefing_at = str(briefing_state.get("last_briefing_at") or "").strip()
    has_briefed_today = _same_local_day(last_briefing_at, overview["timezone"])
    continue_item = _clean_pauta_item(_choose_continue_item(workspace))
    google_connected = overview["google_integration"]["active_profile_status"] == "connected"
    apple_connected = overview["apple_reminders"]["status"] == "connected"

    actions: list[dict[str, str]] = []
    if missing["generated"] or missing["derived"]:
        actions.append(
            _shell_action(
                "repair",
                "Consertar a estrutura antes de brincar de produtividade",
                f"prumo repair --workspace {workspace_str}",
            )
        )

    actions.append(
        _shell_action(
            "briefing",
            "Rodar o briefing agora" if not has_briefed_today else "Rodar o briefing de novo",
            f"prumo briefing --workspace {workspace_str} --refresh-snapshot",
        )
    )

    if continue_item:
        actions.append(
            _host_prompt_action(
                "continue",
                f"Retomar o que já estava quente: {continue_item}",
                f"Continue pelo item da pauta: {continue_item}",
            )
        )

    actions.append(
        _shell_action(
            "context",
            "Ver o estado técnico sem poesia",
            f"prumo context-dump --workspace {workspace_str} --format json",
        )
    )

    if not google_connected:
        actions.append(_suggest_google_auth_action(workspace))

    if not apple_connected:
        actions.append(
            _shell_action(
                "auth-apple-reminders",
                "Conectar Apple Reminders",
                f"prumo auth apple-reminders --workspace {workspace_str}",
            )
        )

    ordered: list[dict[str, str]] = []
    seen: set[str] = set()
    for action in actions:
        if action["id"] in seen:
            continue
        ordered.append(action)
        seen.add(action["id"])
    return ordered[:6]


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
        "structured_entrypoint": {
            "kind": "shell",
            "shell_command": f"prumo start --workspace {workspace_str} --format json",
        },
        "behavior": {
            "short_invocation": "run preferred_entrypoint",
            "explicit_briefing": "run briefing_entrypoint",
            "structured_actions": "prefer structured_entrypoint and obey actions[].kind",
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
    briefing_state = load_json(workspace / "_state" / "briefing-state.json")
    last_briefing_at = str(briefing_state.get("last_briefing_at") or "").strip()
    has_briefed_today = _same_local_day(last_briefing_at, timezone_name)
    last_briefing_clock = _short_clock(last_briefing_at, timezone_name)
    actions = _build_actions(workspace, overview)

    if missing["generated"] or missing["derived"]:
        suggestion = "consertar a estrutura antes de brincar de produtividade."
    elif not has_briefed_today:
        suggestion = "rodar o briefing agora."
    elif _choose_continue_item(workspace):
        suggestion = "retomar a frente mais quente em vez de pedir outro mapa da cidade."
    else:
        suggestion = "rodar o briefing de novo ou abrir o contexto técnico, porque o terreno parece relativamente calmo."

    lines = [
        f"1. {overview['user_name']}, o Prumo está de pé no workspace `{workspace}`.",
        (
            "2. Estado rápido: "
            f"Google `{google['active_profile_status']}`, "
            f"Apple Reminders `{apple['status']}`, "
            f"core `{overview['core_version'] or 'ausente'}`."
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
        lines.append("3. O workspace não está 100% inteiro: " + "; ".join(missing_parts) + ".")
        suggestion_index = 4
    else:
        if has_briefed_today and last_briefing_clock:
            lines.append(f"3. Você já passou pelo briefing hoje, às {last_briefing_clock}.")
        else:
            lines.append("3. Ainda não há briefing registrado hoje neste workspace.")
        suggestion_index = 4

    lines.append(f"{suggestion_index}. Minha sugestão: {suggestion}")

    option_labels = list(string.ascii_lowercase)
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
        "google_status": overview["google_integration"]["active_profile_status"],
        "apple_reminders_status": overview["apple_reminders"]["status"],
        "missing": overview["missing"],
        "adapter_hints": _build_adapter_hints(workspace),
        "actions": _build_actions(workspace, overview),
        "message": _render_start_text(workspace, overview),
    }

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    print(payload["message"])
    return 0
