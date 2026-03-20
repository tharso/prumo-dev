from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

APPLE_REMINDERS_RELATIVE = "_state/apple-reminders-integration.json"
APPLE_REMINDERS_SNAPSHOT_RELATIVE = "_state/apple-reminders-snapshot.json"
DEFAULT_APPLE_REMINDERS_CACHE_MINUTES = 30


def now_iso(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).replace(microsecond=0).isoformat()


def raise_workspace_error(message: str) -> None:
    from prumo_runtime.workspace import WorkspaceError

    raise WorkspaceError(message)


def default_apple_reminders_payload() -> dict:
    return {
        "provider": "apple-reminders",
        "strategy": "eventkit-local",
        "status": "disconnected",
        "authorization_status": "unknown",
        "last_authenticated_at": "",
        "last_refresh_at": "",
        "last_error": "",
        "lists": [],
        "observed_lists": [],
    }


def render_apple_reminders_json() -> str:
    return json.dumps(default_apple_reminders_payload(), ensure_ascii=True, indent=2) + "\n"


def load_apple_reminders(workspace: Path) -> dict:
    target = workspace / APPLE_REMINDERS_RELATIVE
    if not target.exists():
        return default_apple_reminders_payload()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return default_apple_reminders_payload()
    default_payload = default_apple_reminders_payload()
    return {
        "provider": str(payload.get("provider") or default_payload["provider"]),
        "strategy": str(payload.get("strategy") or default_payload["strategy"]),
        "status": str(payload.get("status") or default_payload["status"]),
        "authorization_status": str(payload.get("authorization_status") or default_payload["authorization_status"]),
        "last_authenticated_at": str(payload.get("last_authenticated_at") or default_payload["last_authenticated_at"]),
        "last_refresh_at": str(payload.get("last_refresh_at") or default_payload["last_refresh_at"]),
        "last_error": str(payload.get("last_error") or default_payload["last_error"]),
        "lists": list(payload.get("lists") or default_payload["lists"]),
        "observed_lists": list(payload.get("observed_lists") or default_payload["observed_lists"]),
    }


def default_apple_reminders_snapshot_payload() -> dict:
    return {
        "cached_at": "",
        "status": "empty",
        "note": "",
        "lists": [],
        "observed_lists": [],
        "items": [],
    }


def render_apple_reminders_snapshot_json() -> str:
    return json.dumps(default_apple_reminders_snapshot_payload(), ensure_ascii=True, indent=2) + "\n"


def load_apple_reminders_snapshot(workspace: Path) -> dict:
    target = workspace / APPLE_REMINDERS_SNAPSHOT_RELATIVE
    if not target.exists():
        return default_apple_reminders_snapshot_payload()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return default_apple_reminders_snapshot_payload()
    default_payload = default_apple_reminders_snapshot_payload()
    return {
        "cached_at": str(payload.get("cached_at") or default_payload["cached_at"]),
        "status": str(payload.get("status") or default_payload["status"]),
        "note": str(payload.get("note") or default_payload["note"]),
        "lists": list(payload.get("lists") or default_payload["lists"]),
        "observed_lists": list(payload.get("observed_lists") or default_payload["observed_lists"]),
        "items": list(payload.get("items") or default_payload["items"]),
    }


def write_apple_reminders_snapshot(workspace: Path, payload: dict) -> None:
    target = workspace / APPLE_REMINDERS_SNAPSHOT_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_apple_reminders(workspace: Path, payload: dict) -> None:
    target = workspace / APPLE_REMINDERS_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def update_apple_reminders_state(
    workspace: Path,
    *,
    status: str,
    authorization_status: str,
    timezone_name: str,
    strategy: str | None = None,
    lists: list[str] | None = None,
    observed_lists: list[str] | None = None,
    last_error: str = "",
    authenticated: bool = False,
) -> dict:
    payload = load_apple_reminders(workspace)
    payload.update(
        {
            "strategy": str(strategy or payload.get("strategy") or "eventkit-local"),
            "status": status,
            "authorization_status": authorization_status,
            "last_refresh_at": now_iso(timezone_name),
            "last_error": last_error.strip(),
        }
    )
    if lists is not None:
        payload["lists"] = lists
    if observed_lists is not None:
        payload["observed_lists"] = observed_lists
    if authenticated:
        payload["last_authenticated_at"] = now_iso(timezone_name)
    write_apple_reminders(workspace, payload)
    return payload


def apple_reminders_summary(workspace: Path) -> dict:
    return load_apple_reminders(workspace)


def helper_script_path(workspace: Path) -> Path:
    del workspace
    return Path(__file__).resolve().parent / "helpers" / "apple_reminders.swift"


def applescript_helper_path(workspace: Path) -> Path:
    del workspace
    return Path(__file__).resolve().parent / "helpers" / "apple_reminders.applescript"


def parse_applescript_output(output: str) -> dict[str, Any]:
    status = "error"
    authorization_status = "unknown"
    lists: list[str] = []
    today: list[dict[str, str]] = []
    note = ""
    error = ""
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("STATUS:"):
            status = line.split(":", 1)[1].strip() or status
        elif line.startswith("AUTHORIZATION:"):
            authorization_status = line.split(":", 1)[1].strip() or authorization_status
        elif line.startswith("LIST:"):
            item = line.split(":", 1)[1].strip()
            if item:
                lists.append(item)
        elif line.startswith("ITEM:"):
            payload = line.split(":", 1)[1].strip()
            if payload:
                parts = payload.split("\t")
                if len(parts) >= 4:
                    today.append(
                        {
                            "title": parts[0].strip(),
                            "list": parts[1].strip(),
                            "label": parts[2].strip(),
                            "display": parts[3].strip(),
                        }
                    )
                else:
                    today.append({"display": payload})
        elif line.startswith("NOTE:"):
            note = line.split(":", 1)[1].strip()
        elif line.startswith("ERROR:"):
            error = line.split(":", 1)[1].strip()
    return {
        "strategy": "applescript-local",
        "status": status,
        "authorization_status": authorization_status,
        "lists": lists,
        "today": today,
        "note": note,
        "error": error,
    }


def run_applescript_helper(workspace: Path, action: str, observed_lists: list[str] | None = None) -> dict[str, Any]:
    script = applescript_helper_path(workspace)
    if not script.exists():
        raise_workspace_error(f"helper Apple Reminders (AppleScript) ausente: {script}")
    command = ["osascript", str(script), action]
    for item in observed_lists or []:
        cleaned = str(item).strip()
        if cleaned:
            command.extend(["--list", cleaned])
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=45,
            check=True,
        )
    except subprocess.TimeoutExpired:
        raise_workspace_error(
            "AppleScript de Reminders passou do limite; ou a permissao ficou pendurada, ou o macOS resolveu fazer ioga."
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        raise_workspace_error(stderr or "AppleScript de Reminders falhou sem explicação decente")
    payload = parse_applescript_output(completed.stdout)
    if str(payload.get("status") or "") == "error":
        return payload
    if payload.get("authorization_status") == "unknown":
        payload["authorization_status"] = "authorized"
    return payload


def run_swift_helper(
    workspace: Path,
    action: str,
    timezone_name: str,
    observed_lists: list[str] | None = None,
) -> dict[str, Any]:
    script = helper_script_path(workspace)
    if not script.exists():
        raise_workspace_error(f"helper Apple Reminders ausente: {script}")
    command = ["swift", str(script), action, "--timezone", timezone_name]
    for item in observed_lists or []:
        cleaned = str(item).strip()
        if cleaned:
            command.extend(["--list", cleaned])
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        raise_workspace_error(stderr or "helper Apple Reminders falhou sem explicação decente")
    except subprocess.TimeoutExpired:
        raise_workspace_error("helper Apple Reminders passou do limite; a Apple também sabe se atrasar")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise_workspace_error("helper Apple Reminders respondeu lixo onde devia haver JSON")
    if not isinstance(payload, dict):
        raise_workspace_error("helper Apple Reminders respondeu formato inválido")
    payload.setdefault("strategy", "eventkit-local")
    return payload


def run_apple_reminders_helper(
    workspace: Path,
    action: str,
    timezone_name: str,
    observed_lists: list[str] | None = None,
) -> dict[str, Any]:
    from prumo_runtime.workspace import WorkspaceError

    try:
        return run_swift_helper(workspace, action, timezone_name, observed_lists)
    except WorkspaceError as exc:
        swift_message = str(exc)
        if action == "fetch":
            try:
                return run_applescript_helper(workspace, action, observed_lists)
            except WorkspaceError:
                raise_workspace_error(swift_message)
        try:
            return run_applescript_helper(workspace, action, observed_lists)
        except WorkspaceError:
            raise_workspace_error(swift_message)


def auth_apple_reminders(workspace: Path, timezone_name: str) -> dict:
    payload = run_apple_reminders_helper(workspace, "auth", timezone_name)
    status = str(payload.get("status") or "error")
    auth_status = str(payload.get("authorization_status") or "unknown")
    lists = [str(item) for item in payload.get("lists", []) if str(item).strip()]
    last_error = str(payload.get("error") or "")
    return update_apple_reminders_state(
        workspace,
        status=status,
        authorization_status=auth_status,
        timezone_name=timezone_name,
        strategy=str(payload.get("strategy") or "eventkit-local"),
        lists=lists,
        observed_lists=load_apple_reminders(workspace).get("observed_lists") or [],
        last_error=last_error,
        authenticated=status == "connected",
    )


def set_observed_apple_reminders_lists(workspace: Path, timezone_name: str, observed_lists: list[str]) -> dict:
    current = load_apple_reminders(workspace)
    cleaned = [str(item).strip() for item in observed_lists if str(item).strip()]
    return update_apple_reminders_state(
        workspace,
        status=str(current.get("status") or "disconnected"),
        authorization_status=str(current.get("authorization_status") or "unknown"),
        timezone_name=timezone_name,
        strategy=str(current.get("strategy") or "eventkit-local"),
        lists=list(current.get("lists") or []),
        observed_lists=cleaned,
        last_error=str(current.get("last_error") or ""),
        authenticated=False,
    )


def snapshot_age_minutes(workspace: Path, timezone_name: str) -> int | None:
    cached_at = str(load_apple_reminders_snapshot(workspace).get("cached_at") or "").strip()
    if not cached_at:
        return None
    try:
        cached_dt = datetime.fromisoformat(cached_at)
    except ValueError:
        return None
    now = datetime.now(ZoneInfo(timezone_name))
    return max(0, int((now - cached_dt).total_seconds() // 60))


def fetch_apple_reminders_today(
    workspace: Path,
    timezone_name: str,
    *,
    refresh: bool = False,
    max_cache_age_minutes: int = DEFAULT_APPLE_REMINDERS_CACHE_MINUTES,
) -> dict[str, Any]:
    state_before = load_apple_reminders(workspace)
    observed_lists = [str(item).strip() for item in state_before.get("observed_lists") or [] if str(item).strip()]
    cached = load_apple_reminders_snapshot(workspace)
    cache_age = snapshot_age_minutes(workspace, timezone_name)
    if (
        not refresh
        and cached.get("status") == "ok"
        and cache_age is not None
        and cache_age <= max_cache_age_minutes
    ):
        note = str(cached.get("note") or "").strip()
        if note:
            note = f"{note} Cache local de Apple Reminders reaproveitado ({cache_age} min atrás)."
        else:
            note = f"Cache local de Apple Reminders reaproveitado ({cache_age} min atrás)."
        return {
            "status": "cache",
            "authorization_status": str(state_before.get("authorization_status") or "unknown"),
            "lists": list(cached.get("lists") or []),
            "observed_lists": list(cached.get("observed_lists") or []),
            "items": list(cached.get("items") or []),
            "raw_items": [],
            "note": note,
            "state": state_before,
        }

    payload = run_apple_reminders_helper(workspace, "fetch", timezone_name, observed_lists)
    status = str(payload.get("status") or "error")
    auth_status = str(payload.get("authorization_status") or "unknown")
    lists = [str(item) for item in payload.get("lists", []) if str(item).strip()]
    last_error = str(payload.get("error") or "")
    state = update_apple_reminders_state(
        workspace,
        status="connected" if status == "ok" else status,
        authorization_status=auth_status,
        timezone_name=timezone_name,
        strategy=str(payload.get("strategy") or "eventkit-local"),
        lists=lists,
        observed_lists=observed_lists,
        last_error=last_error,
        authenticated=False,
    )
    items = payload.get("today", [])
    rendered = [str(item.get("display") or "").strip() for item in items if isinstance(item, dict) and str(item.get("display") or "").strip()]
    note = str(payload.get("note") or "").strip()
    write_apple_reminders_snapshot(
        workspace,
        {
            "cached_at": now_iso(timezone_name),
            "status": status,
            "note": note,
            "lists": lists,
            "observed_lists": observed_lists,
            "items": rendered,
        },
    )
    return {
        "status": status,
        "authorization_status": auth_status,
        "lists": lists,
        "observed_lists": observed_lists,
        "items": rendered,
        "raw_items": items if isinstance(items, list) else [],
        "note": note,
        "state": state,
    }
