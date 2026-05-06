"""
Version check automático — banner educado em stderr (#87).

Verifica versão remota com cache (TTL 24h), mostra banner 1x/24h
para humano em terminal interativo. Silencioso em CI, JSON, pipes.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from prumo_runtime import __version__

REMOTE_VERSION_URL = "https://raw.githubusercontent.com/tharso/prumo/main/VERSION"
DEFAULT_FETCH_TIMEOUT = 1.0
DEFAULT_TTL_HOURS = 24
FAILURE_TTL_HOURS = 1
BANNER_COOLDOWN_HOURS = 24

SUPPRESS_COMMANDS = {"update", "upgrade", "version"}


def check_and_notify(command: str | None, format_arg: str | None) -> None:
    """Entry point: verifica versão e emite banner se necessário."""
    try:
        if _should_suppress(command=command, format_arg=format_arg):
            return

        cache_file = _cache_path()
        cache = _read_cache(cache_file)

        ttl = _get_ttl_hours()

        if _should_fetch(cache, ttl_hours=ttl):
            remote = _fetch_remote_version()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            new_cache: dict[str, Any] = {
                "checked_at": now,
                "remote_version": remote,
                "last_notified_at": cache.get("last_notified_at") if cache else None,
            }
            if remote is None:
                new_cache["failed"] = True
            _write_cache(new_cache, cache_file)
            cache = new_cache

        if cache is None:
            return

        remote_version = cache.get("remote_version")
        last_notified = cache.get("last_notified_at")

        if _should_show_banner(remote_version, __version__, last_notified):
            _emit_banner(remote_version)
            cache["last_notified_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _write_cache(cache, cache_file)
    except Exception:
        pass


def _cache_path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "prumo" / "version-check.json"


def _read_cache(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _write_cache(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix="vc_"
    )
    try:
        os.write(tmp_fd, json.dumps(data, ensure_ascii=False).encode("utf-8"))
        os.close(tmp_fd)
        Path(tmp_path).replace(path)
    except Exception:
        os.close(tmp_fd) if not os.get_inheritable(tmp_fd) else None
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _should_suppress(command: str | None, format_arg: str | None) -> bool:
    if os.environ.get("PRUMO_NO_VERSION_CHECK") == "1":
        return True
    if os.environ.get("CI", "").lower() in ("true", "1"):
        return True
    if os.environ.get("PRUMO_NONINTERACTIVE") == "1":
        return True
    if format_arg == "json":
        return True
    if command in SUPPRESS_COMMANDS:
        return True
    if not sys.stderr.isatty():
        return True
    return False


def _should_fetch(cache: dict[str, Any] | None, ttl_hours: float = DEFAULT_TTL_HOURS) -> bool:
    if cache is None:
        return True
    checked_at = cache.get("checked_at")
    if not checked_at:
        return True

    try:
        checked_time = datetime.datetime.fromisoformat(checked_at)
    except (ValueError, TypeError):
        return True

    now = datetime.datetime.now(datetime.timezone.utc)
    if checked_time.tzinfo is None:
        checked_time = checked_time.replace(tzinfo=datetime.timezone.utc)

    effective_ttl = FAILURE_TTL_HOURS if cache.get("failed") else ttl_hours
    elapsed = (now - checked_time).total_seconds() / 3600
    return elapsed >= effective_ttl


def _should_show_banner(
    remote_version: str | None,
    local_version: str,
    last_notified_at: str | None,
) -> bool:
    if remote_version is None:
        return False

    if not _is_newer(remote_version, local_version):
        return False

    if last_notified_at:
        try:
            notified_time = datetime.datetime.fromisoformat(last_notified_at)
            if notified_time.tzinfo is None:
                notified_time = notified_time.replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            elapsed_hours = (now - notified_time).total_seconds() / 3600
            if elapsed_hours < BANNER_COOLDOWN_HOURS:
                return False
        except (ValueError, TypeError):
            pass

    return True


def _is_newer(remote: str, local: str) -> bool:
    """Compara versões. Tenta packaging.version, fallback pra tupla."""
    try:
        from packaging.version import Version
        return Version(remote) > Version(local)
    except (ImportError, Exception):
        pass
    try:
        r = tuple(int(x) for x in remote.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except (ValueError, AttributeError):
        return False


def _fetch_remote_version() -> str | None:
    try:
        with urllib.request.urlopen(REMOTE_VERSION_URL, timeout=DEFAULT_FETCH_TIMEOUT) as resp:
            return resp.read().decode("utf-8").strip()
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def _emit_banner(remote_version: str) -> None:
    print(
        f"Prumo {remote_version} disponível (você está em {__version__}). "
        f"Rode: prumo update",
        file=sys.stderr,
    )


def _get_ttl_hours() -> float:
    env_val = os.environ.get("PRUMO_VERSION_CHECK_TTL_HOURS")
    if env_val:
        try:
            return float(env_val)
        except ValueError:
            pass
    return DEFAULT_TTL_HOURS
