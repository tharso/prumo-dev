from __future__ import annotations

from pathlib import Path

from prumo_runtime.apple_reminders import auth_apple_reminders, set_observed_apple_reminders_lists
from prumo_runtime.workspace import WorkspaceError, build_config_from_existing


def run_auth_apple_reminders(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    config = build_config_from_existing(workspace)
    print(f"{config.user_name}, vou pedir acesso local aos Apple Reminders deste Mac.", flush=True)
    print(
        "Nada vai para cloud do Prumo. O objetivo aqui é só ler os lembretes locais/sincronizados que a Apple já mostra para você.",
        flush=True,
    )
    observed_lists = [str(item).strip() for item in (getattr(args, "observe_lists", None) or []) if str(item).strip()]
    if observed_lists:
        set_observed_apple_reminders_lists(workspace, config.timezone_name, observed_lists)
    payload = auth_apple_reminders(workspace, config.timezone_name)
    status = str(payload.get("status") or "desconhecido")
    auth_status = str(payload.get("authorization_status") or "unknown")
    print("Apple Reminders processado.")
    print(f"- Workspace: {workspace}")
    print(f"- Status: {status}")
    print(f"- Authorization: {auth_status}")
    lists = payload.get("lists") or []
    print(f"- Listas visíveis: {len(lists)}")
    for item in lists[:5]:
        print(f"  - {item}")
    if observed_lists:
        print(f"- Listas observadas: {', '.join(observed_lists)}")
    if payload.get("last_error"):
        print(f"- Nota: {payload['last_error']}")
    if status not in {"connected", "ok"}:
        raise WorkspaceError(
            "Apple Reminders ainda não ficou acessível. Se a Apple mostrou popup, diga sim antes de culpar o terminal."
        )
    return 0
