from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from prumo_runtime.platform_support import is_macos, platform_label, runtime_app_dir
from prumo_runtime.workspace_paths import workspace_paths

DEFAULT_GOOGLE_PROFILE = "pessoal"
DEFAULT_GOOGLE_SCOPES = (
    "openid",
    "email",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
)
KEYCHAIN_SERVICE_PREFIX = "me.prumo.google.oauth"
UNSET = object()


def keychain_supported() -> bool:
    return is_macos()


def token_storage_backend_type() -> str:
    return "macos-keychain" if keychain_supported() else "runtime-local-file"


def token_storage_secure() -> bool:
    return keychain_supported()


def keychain_service_name() -> str:
    prefix = os.environ.get("PRUMO_GOOGLE_KEYCHAIN_SERVICE_PREFIX", KEYCHAIN_SERVICE_PREFIX).strip()
    return prefix or KEYCHAIN_SERVICE_PREFIX


def keychain_account_name(workspace: Path, profile: str) -> str:
    digest = hashlib.sha256(str(workspace.resolve()).encode("utf-8")).hexdigest()[:16]
    return f"{digest}:{profile}"


def default_token_storage(workspace: Path, profile: str) -> dict:
    storage = {
        "type": token_storage_backend_type(),
        "service": keychain_service_name(),
        "account": keychain_account_name(workspace, profile),
    }
    if storage["type"] == "runtime-local-file":
        service = str(storage["service"])
        account = str(storage["account"])
        digest = hashlib.sha256(f"{service}:{account}".encode("utf-8")).hexdigest()[:24]
        storage["path"] = str(runtime_app_dir() / "secrets" / "google" / f"{digest}.json")
    return storage


def resolve_token_storage(workspace: Path, profile: str) -> dict:
    target = workspace_paths(workspace).google_integration
    if target.exists():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        profiles = payload.get("profiles") if isinstance(payload.get("profiles"), dict) else {}
        profile_payload = profiles.get(profile)
        if isinstance(profile_payload, dict):
            storage = profile_payload.get("token_storage")
            if isinstance(storage, dict) and storage.get("service") and storage.get("account"):
                merged = {
                    **default_token_storage(workspace, profile),
                    "type": str(storage.get("type") or token_storage_backend_type()),
                    "service": str(storage["service"]),
                    "account": str(storage["account"]),
                }
                if storage.get("path"):
                    merged["path"] = str(storage["path"])
                return merged
    return default_token_storage(workspace, profile)


def default_profile_state(workspace: Path, profile: str = DEFAULT_GOOGLE_PROFILE) -> dict:
    storage = resolve_token_storage(workspace, profile)
    return {
        "label": "Conta pessoal" if profile == "pessoal" else f"Conta {profile}",
        "status": "disconnected",
        "account_email": "",
        "scopes": list(DEFAULT_GOOGLE_SCOPES),
        "last_authenticated_at": "",
        "last_refresh_at": "",
        "last_error": "",
        "source": "browser-oauth",
        "token_storage": storage,
    }


def default_google_integration_payload(workspace: Path) -> dict:
    return {
        "provider": "google",
        "strategy": "direct-google-api",
        "status": "disconnected",
        "active_profile": DEFAULT_GOOGLE_PROFILE,
        "profiles": {
            DEFAULT_GOOGLE_PROFILE: default_profile_state(workspace, DEFAULT_GOOGLE_PROFILE),
        },
    }


def render_google_integration_json(workspace: Path) -> str:
    return json.dumps(default_google_integration_payload(workspace), ensure_ascii=True, indent=2) + "\n"


def load_google_integration(workspace: Path) -> dict:
    target = workspace_paths(workspace).google_integration
    if not target.exists():
        return default_google_integration_payload(workspace)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return default_google_integration_payload(workspace)

    default_payload = default_google_integration_payload(workspace)
    profiles = payload.get("profiles") if isinstance(payload.get("profiles"), dict) else {}
    merged_profiles = dict(default_payload["profiles"])
    for name, profile_payload in profiles.items():
        base = default_profile_state(workspace, name)
        if isinstance(profile_payload, dict):
            merged = {**base, **profile_payload}
            token_storage = {**base["token_storage"], **(profile_payload.get("token_storage") or {})}
            merged["token_storage"] = token_storage
            merged_profiles[name] = merged

    return {
        "provider": str(payload.get("provider") or default_payload["provider"]),
        "strategy": str(payload.get("strategy") or default_payload["strategy"]),
        "status": str(payload.get("status") or default_payload["status"]),
        "active_profile": str(payload.get("active_profile") or default_payload["active_profile"]),
        "profiles": merged_profiles,
    }


def write_google_integration(workspace: Path, payload: dict) -> None:
    target = workspace_paths(workspace).google_integration
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def update_profile_state(
    workspace: Path,
    profile: str,
    *,
    status: str,
    account_email: str = "",
    scopes: list[str] | None = None,
    last_authenticated_at: str = "",
    last_refresh_at: str = "",
    last_error: str | None | object = UNSET,
) -> dict:
    payload = load_google_integration(workspace)
    profile_payload = payload["profiles"].get(profile, default_profile_state(workspace, profile))
    profile_payload.update(
        {
            "status": status,
            "account_email": account_email,
            "scopes": scopes or profile_payload.get("scopes") or list(DEFAULT_GOOGLE_SCOPES),
            "last_authenticated_at": last_authenticated_at or profile_payload.get("last_authenticated_at", ""),
            "last_refresh_at": last_refresh_at or profile_payload.get("last_refresh_at", ""),
            "source": "browser-oauth",
        }
    )
    if last_error is not UNSET:
        profile_payload["last_error"] = str(last_error or "").strip()
    payload["profiles"][profile] = profile_payload
    payload["active_profile"] = profile
    payload["status"] = "connected" if any(
        item.get("status") == "connected" for item in payload["profiles"].values()
    ) else status
    write_google_integration(workspace, payload)
    return payload


def google_integration_summary(workspace: Path) -> dict:
    payload = load_google_integration(workspace)
    profiles = payload.get("profiles") or {}
    active_profile = str(payload.get("active_profile") or DEFAULT_GOOGLE_PROFILE)
    active_payload = profiles.get(active_profile) if isinstance(profiles.get(active_profile), dict) else {}
    connected_profiles = [
        name
        for name, profile_payload in profiles.items()
        if isinstance(profile_payload, dict) and profile_payload.get("status") == "connected"
    ]
    return {
        "provider": payload.get("provider", "google"),
        "strategy": payload.get("strategy", "direct-google-api"),
        "status": payload.get("status", "disconnected"),
        "active_profile": active_profile,
        "active_profile_status": str(active_payload.get("status") or "disconnected"),
        "active_account_email": str(active_payload.get("account_email") or ""),
        "active_last_authenticated_at": str(active_payload.get("last_authenticated_at") or ""),
        "active_last_refresh_at": str(active_payload.get("last_refresh_at") or ""),
        "active_last_error": str(active_payload.get("last_error") or ""),
        "connected_profiles": connected_profiles,
        "profiles": profiles,
        "token_storage_supported": True,
        "token_storage_secure": token_storage_secure(),
        "token_storage_backend": token_storage_backend_type(),
    }


def runtime_secret_store_path(workspace: Path, profile: str, storage: dict | None = None) -> Path:
    chosen = storage or resolve_token_storage(workspace, profile)
    service = str(chosen.get("service") or keychain_service_name())
    account = str(chosen.get("account") or keychain_account_name(workspace, profile))
    digest = hashlib.sha256(f"{service}:{account}".encode("utf-8")).hexdigest()[:24]
    return runtime_app_dir() / "secrets" / "google" / f"{digest}.json"


def store_token_in_keychain(workspace: Path, profile: str, secret: str) -> dict:
    if not keychain_supported():
        raise RuntimeError("Keychain do macOS indisponivel neste sistema")
    service = keychain_service_name()
    account = keychain_account_name(workspace, profile)
    command = [
        "security",
        "add-generic-password",
        "-a",
        account,
        "-s",
        service,
        "-w",
        secret,
        "-U",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("comando `security` indisponivel; sem isso o Keychain nao entra em cena") from exc
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(stderr or "nao foi possivel gravar token no Keychain")
    return {"type": "macos-keychain", "service": service, "account": account}


def store_token_in_runtime_file(workspace: Path, profile: str, secret: str) -> dict:
    storage = resolve_token_storage(workspace, profile)
    path = runtime_secret_store_path(workspace, profile, storage=storage)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(secret, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return {
        "type": "runtime-local-file",
        "service": storage["service"],
        "account": storage["account"],
        "path": str(path),
    }


def load_secret_from_keychain(workspace: Path, profile: str) -> str:
    if not keychain_supported():
        raise RuntimeError("Keychain do macOS indisponivel neste sistema")
    storage = resolve_token_storage(workspace, profile)
    service = storage["service"]
    account = storage["account"]
    command = [
        "security",
        "find-generic-password",
        "-a",
        account,
        "-s",
        service,
        "-w",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("comando `security` indisponivel; sem isso o Keychain nao entra em cena") from exc
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(stderr or "nao foi possivel ler token do Keychain")
    return completed.stdout.strip()


def load_secret_from_runtime_file(workspace: Path, profile: str) -> str:
    storage = resolve_token_storage(workspace, profile)
    raw_path = str(storage.get("path") or "")
    path = Path(raw_path) if raw_path else runtime_secret_store_path(workspace, profile, storage=storage)
    if not path.exists():
        raise RuntimeError(
            f"credencial Google ausente no storage local do runtime ({path}). Sem isso o refresh nao tem nem de onde sair."
        )
    return path.read_text(encoding="utf-8")


def store_token(workspace: Path, profile: str, secret: str) -> dict:
    if keychain_supported():
        return store_token_in_keychain(workspace, profile, secret)
    return store_token_in_runtime_file(workspace, profile, secret)


def load_secret(workspace: Path, profile: str) -> str:
    storage = resolve_token_storage(workspace, profile)
    if storage["type"] == "macos-keychain":
        return load_secret_from_keychain(workspace, profile)
    if storage["type"] == "runtime-local-file":
        return load_secret_from_runtime_file(workspace, profile)
    raise RuntimeError(f"storage de token `{storage['type']}` ainda nao foi implementado com juizo")


def describe_token_storage() -> str:
    if keychain_supported():
        return "Keychain do macOS"
    return f"storage local do runtime em {platform_label()} (fora do workspace)"


def store_oauth_bundle(workspace: Path, profile: str, bundle: dict[str, Any]) -> dict:
    return store_token(workspace, profile, json.dumps(bundle, ensure_ascii=True))


def store_oauth_bundle_in_keychain(workspace: Path, profile: str, bundle: dict[str, Any]) -> dict:
    return store_oauth_bundle(workspace, profile, bundle)


def load_oauth_bundle_from_keychain(workspace: Path, profile: str) -> dict[str, Any]:
    raw = load_secret(workspace, profile)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("token no storage do runtime esta ilegivel; alguem guardou um tijolo onde devia haver JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("token no storage do runtime nao tem formato valido")
    return payload


def load_oauth_bundle(workspace: Path, profile: str) -> dict[str, Any]:
    return load_oauth_bundle_from_keychain(workspace, profile)
