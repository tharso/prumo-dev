"""
Version check — cache TTL 24h com produtor explícito (#87 → #195).

O PRODUTOR do cache é `prumo version-check --ensure-fresh` (preflight do
briefing): rede no máximo 1x/24h, falha re-tenta em 1h. O banner (#87) é
cache-only — notifica humano em terminal interativo 1x/24h a partir do
cache e escreve apenas `last_notified_at` (nunca busca rede nem produz
versão). Silencioso em CI, JSON, pipes.
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

# "fim" entra aqui (#174): o /fim promete read-only — o banner (hoje
# cache-only, #195) ainda escreveria `last_notified_at` no `prumo fim` textual.
# "version-check" (#195): o comando É a checagem; banner em cima seria eco.
# "projetos" (#201): o report promete read-only — o banner escreveria last_notified_at.
SUPPRESS_COMMANDS = {"update", "upgrade", "version", "fim", "version-check", "projetos"}


def check_and_notify(command: str | None, format_arg: str | None) -> None:
    """Entry point: emite banner a partir do CACHE — nunca busca rede (#195).

    O produtor único do cache é `prumo version-check --ensure-fresh`
    (preflight do briefing). O banner apenas notifica o que o cache já sabe;
    sem cache populado, silêncio. Margem aceita e registrada no DECISIONS.md:
    quem nunca roda o preflight não vê banner.
    """
    try:
        if _should_suppress(command=command, format_arg=format_arg):
            return

        cache_file = _cache_path()
        cache = _read_cache(cache_file)

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
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    # JSON válido que não é objeto (lista, string, número) é cache
    # estruturalmente inválido — tratar como ausente (#195, Codex achado 4).
    if not isinstance(data, dict):
        return None
    return data


def _write_cache(data: dict[str, Any], path: Path) -> bool:
    """Grava o cache atomicamente. Devolve False em falha (nunca levanta)."""
    tmp_fd = None
    tmp_path = None
    closed = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent), suffix=".tmp", prefix="vc_"
        )
        os.write(tmp_fd, json.dumps(data, ensure_ascii=False).encode("utf-8"))
        os.close(tmp_fd)
        closed = True
        Path(tmp_path).replace(path)
        return True
    except Exception:
        if tmp_fd is not None and not closed:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return False


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
    """Compara versões semver (N.N.N). Canal VERSION garante formato simples."""
    try:
        r = tuple(int(x) for x in remote.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except (ValueError, AttributeError):
        return False


def ensure_fresh_status(*, allow_network: bool) -> dict[str, Any]:
    """Status do cache de versão; com `allow_network`, refresca se stale (#195).

    É o PRODUTOR do cache no fluxo do briefing: busca e grava no máximo
    1x/TTL (24h; falha re-tenta em 1h). Sem `allow_network`, zero rede —
    apenas reporta o cache atual. Nunca levanta: falha vira status.
    """
    cache_file = _cache_path()
    cache = _read_cache(cache_file)
    ttl = _get_ttl_hours()
    source = "cache" if cache is not None else "no_cache"
    cache_write_failed = False

    if allow_network and _should_fetch(cache, ttl_hours=ttl):
        remote = _fetch_remote_version()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        new_cache: dict[str, Any] = {
            "checked_at": now,
            "remote_version": remote,
            "last_notified_at": cache.get("last_notified_at") if cache else None,
        }
        if remote is None:
            new_cache["failed"] = True
        cache_write_failed = not _write_cache(new_cache, cache_file)
        cache = new_cache
        if remote is None:
            source = "fetch_failed"
        elif cache_write_failed:
            # Buscou mas não persistiu: o dado vale pra ESTA resposta, mas o
            # próximo briefing vai rebuscar — não fingir cache saudável.
            source = "fetched_unpersisted"
        else:
            source = "fetched"
    elif cache is not None and cache.get("failed"):
        # Falha persistida nunca passa por cache saudável (#195, Codex
        # achado 3). Dentro do cooldown (FAILURE_TTL_HOURS) é
        # "failure_cooldown"; vencido o cooldown sem rede permitida nesta
        # chamada, é "stale_failure" — re-tentável no próximo ensure-fresh.
        if _should_fetch(cache, ttl_hours=ttl):
            source = "stale_failure"
        else:
            source = "failure_cooldown"

    remote_version = (cache or {}).get("remote_version")
    failed = bool((cache or {}).get("failed"))
    return {
        "local_version": __version__,
        "remote_version": remote_version,
        "checked_at": (cache or {}).get("checked_at"),
        "fresh": (
            cache is not None
            and not failed
            and not cache_write_failed
            and not _should_fetch(cache, ttl_hours=ttl)
        ),
        "failed": failed,
        "cache_write_failed": cache_write_failed,
        "source": source,
        "update_available": bool(
            remote_version and _is_newer(remote_version, __version__)
        ),
    }


def read_cached_remote_version() -> str | None:
    """Lê a versão remota do cache SEM buscar na rede.

    O briefing (`prumo briefing --format json`) usa isto para computar a
    severidade da defasagem sem adicionar latência: o cache é populado pelo
    produtor explícito (`prumo version-check --ensure-fresh`, #195). Devolve
    a última versão conhecida mesmo com TTL vencido (staleness é problema do
    preflight, não do painel); se o cache não existe ou não tem versão,
    devolve None e o agente cai no Passo 2 do `version-update.md`.
    """
    cache = _read_cache(_cache_path())
    if not cache:
        return None
    remote = cache.get("remote_version")
    return remote if isinstance(remote, str) else None


def _minor_distance(local: tuple[int, ...], remote: tuple[int, ...]) -> int:
    """Quantos *minor* o remoto está à frente do local. Major diferente = longe."""
    lm = local + (0,) * (3 - len(local))
    rm = remote + (0,) * (3 - len(remote))
    if rm[0] != lm[0]:
        return 99  # salto de major — sempre alerta
    return rm[1] - lm[1]


def compute_staleness(local: str, remote: str | None) -> dict[str, Any]:
    """Severidade da defasagem por **distância de versão** (fonte de verdade deste elo).

    A dimensão "M dias parada" NÃO vem daqui — vem do `lastUpdated` do checkout
    do marketplace, computado pelo doctor (módulo `doctor.md`; ver `version-update.md` → fonte de
    verdade por elo). Aqui é só distância de versão: instalada (core do
    workspace) vs. pública.

    Severidade: `ok` (em dia) · `info` (só patch atrás) · `warning` (1 minor
    atrás) · `alert` (2+ minor, ou salto de major) · `unknown` (sem remoto).
    """
    if not remote:
        return {"severity": "unknown", "minor_behind": 0, "local": local, "remote": None,
                "reason": "versão pública ainda não checada"}
    try:
        rv = tuple(int(x) for x in remote.split("."))
        lv = tuple(int(x) for x in local.split("."))
    except (ValueError, AttributeError):
        return {"severity": "unknown", "minor_behind": 0, "local": local, "remote": remote,
                "reason": "versão ilegível"}
    if rv <= lv:
        return {"severity": "ok", "minor_behind": 0, "local": local, "remote": remote,
                "reason": "em dia com a versão pública"}
    behind = _minor_distance(lv, rv)
    if rv[0] != lv[0]:
        # Salto de major — `behind` é sentinela (99), não uma contagem real.
        # Nunca vazar "99 versões atrás" pro usuário (era o caso 4.7.0→5.x).
        severity = "alert"
        reason = f"salto de versão major: instalada {local}, pública {remote}"
    elif behind >= 2:
        severity, reason = "alert", f"{behind} versões atrás da pública ({remote})"
    elif behind == 1:
        severity, reason = "warning", f"uma versão atrás da pública ({remote})"
    else:
        severity, reason = "info", f"um patch atrás da pública ({remote})"
    return {"severity": severity, "minor_behind": behind, "local": local, "remote": remote,
            "reason": reason}


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
