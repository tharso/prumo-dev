"""
Comando `prumo update` — atualiza o runtime instalado.

Detecta como o runtime foi instalado via marker JSON granular (schema v1.0)
em `~/.local/share/prumo/install-method.json`. Sem marker, faz fallback via
importlib.metadata. Suporta --dry-run, --check, --yes e --format json.

Issue de origem: #86.
"""
from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from prumo_runtime import __version__


REMOTE_VERSION_URL = "https://raw.githubusercontent.com/tharso/prumo/main/VERSION"
DEFAULT_FETCH_TIMEOUT_SECONDS = 2.5
CURL_INSTALL_URL = (
    "https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_runtime_install.sh"
)
UPDATE_CHANNEL = "latest em main"


def install_marker_path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "prumo" / "install-method.json"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "prumo" / "install-method.json"


def detect_install_method(marker_path: Path | None = None) -> dict[str, Any]:
    """
    Detecta como o runtime foi instalado.

    Retorna dict com campos do schema granular v1.0:
        launcher, package_manager, source_kind, source (marker|fallback),
        is_editable, details, e opcionalmente warning.
    """
    target = marker_path if marker_path is not None else install_marker_path()
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return _parse_marker(data)
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: importlib.metadata
    try:
        importlib.metadata.version("prumo-runtime")
        return {
            "launcher": "unknown",
            "package_manager": "pip-user",
            "source_kind": "unknown",
            "source": "fallback",
            "is_editable": False,
            "details": {"reason": "importlib.metadata found prumo-runtime"},
        }
    except Exception:
        pass

    return {
        "launcher": "unknown",
        "package_manager": "unknown",
        "source_kind": "unknown",
        "source": "fallback",
        "is_editable": False,
        "details": {
            "reason": "no marker found and importlib.metadata cannot resolve prumo-runtime",
        },
    }


def _parse_marker(data: dict) -> dict[str, Any]:
    """Parseia marker JSON — suporta schema v1.0 e legado."""
    if data.get("schema_version") == "1.0":
        result: dict[str, Any] = {
            "launcher": data.get("launcher", "unknown"),
            "package_manager": data.get("package_manager", "unknown"),
            "source_kind": data.get("source_kind", "unknown"),
            "source": "marker",
            "is_editable": data.get("source_kind") == "editable",
            "details": data,
        }
        marker_python = data.get("python")
        if marker_python and marker_python != sys.executable:
            result["warning"] = (
                f"Python no marker ({marker_python}) diverge do runtime atual "
                f"({sys.executable}). Pode ser instalação diferente."
            )
        return result

    # Legado: {"method": "curl"|"pip", ...}
    method = data.get("method", "unknown")
    if method == "curl":
        return {
            "launcher": "install-script",
            "package_manager": "unknown",
            "source_kind": data.get("source_kind", "unknown"),
            "source": "marker",
            "is_editable": False,
            "details": data,
        }
    if method == "pip":
        return {
            "launcher": "manual",
            "package_manager": "pip-user",
            "source_kind": data.get("source_kind", "unknown"),
            "source": "marker",
            "is_editable": False,
            "details": data,
            "warning": (
                "Marker legado (sem schema_version). Detecção limitada: "
                "sem python, prumo_executable ou source_kind confirmados."
            ),
        }
    return {
        "launcher": "unknown",
        "package_manager": "unknown",
        "source_kind": "unknown",
        "source": "marker",
        "is_editable": False,
        "details": data,
    }


def fetch_remote_version(
    url: str = REMOTE_VERSION_URL,
    timeout: float = DEFAULT_FETCH_TIMEOUT_SECONDS,
) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8").strip()
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def build_update_plan(
    package_manager: str,
    current_version: str,
    remote_version: str | None,
    source_kind: str = "unknown",
    launcher: str = "unknown",
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "current_version": current_version,
        "remote_version": remote_version,
        "needs_update": False,
        "command": None,
        "explanation": None,
    }

    if remote_version is None:
        plan["explanation"] = (
            "Não foi possível verificar versão remota (offline ou rede falhou). "
            "Tente novamente quando houver conexão."
        )
        return plan

    if remote_version == current_version:
        plan["explanation"] = (
            f"Runtime já está em {current_version} (igual à versão remota)."
        )
        return plan

    # Versão local maior que remota — não fazer downgrade
    if _version_tuple(current_version) > _version_tuple(remote_version):
        plan["explanation"] = (
            f"Versão local ({current_version}) é mais recente que a remota "
            f"({remote_version}). Nenhuma ação necessária."
        )
        return plan

    plan["needs_update"] = True

    # Editable install — não auto-atualizar
    if source_kind == "editable":
        plan["command"] = None
        plan["explanation"] = (
            f"Instalação editable detectada. Não é possível auto-atualizar. "
            f"Rode `git pull` no checkout local e reinstale."
        )
        return plan

    # Install-script: sempre re-executa o script (garante canal "latest em main")
    if launcher == "install-script":
        plan["command"] = "install-script"
        plan["explanation"] = (
            f"Atualiza runtime de {current_version} pra {remote_version} "
            "re-executando o install script (canal: latest em main)."
        )
        return plan

    # Manual/pip direto do registry (canal PyPI, não main)
    if package_manager in ("pip-user", "pipx"):
        plan["command"] = "pip install --upgrade prumo-runtime"
        plan["explanation"] = (
            f"Atualiza runtime de {current_version} pra {remote_version} via pip (registry)."
        )
    elif package_manager == "uv-tool":
        plan["command"] = "uv tool install --force prumo-runtime"
        plan["explanation"] = (
            f"Atualiza runtime de {current_version} pra {remote_version} via uv (registry)."
        )
    else:
        plan["command"] = None
        plan["explanation"] = (
            "Método de instalação não detectado. Reinstale manualmente via pip "
            "(`pip install --upgrade prumo-runtime`) ou via install script."
        )

    return plan


def _version_tuple(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


def _confirm_update(plan: dict, method_info: dict) -> bool:
    """Pede confirmação interativa. Retorna True se confirmado."""
    if not sys.stdin.isatty():
        print("Erro: update requer confirmação interativa. Use --yes para automação.")
        return False
    prompt = (
        f"Confirma update de {plan['current_version']} → {plan['remote_version']} "
        f"via {method_info['package_manager']}? [y/N] "
    )
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes", "s", "sim")


def _download_install_script() -> str:
    """Baixa install script pra temp file. Retorna path. Caller limpa."""
    assert CURL_INSTALL_URL.startswith("https://"), "URL do install script deve ser HTTPS"
    fd, path = tempfile.mkstemp(suffix=".sh", prefix="prumo_install_")
    os.close(fd)
    try:
        with urllib.request.urlopen(CURL_INSTALL_URL, timeout=30) as response:
            data = response.read()
        Path(path).write_bytes(data)
    except Exception:
        os.unlink(path)
        raise
    return path


def _execute_plan(plan: dict, method: str) -> int:
    """Executa o plano. Retorna exit code."""
    if method in ("pip-user", "pipx"):
        return subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "prumo-runtime"],
        ).returncode

    if method == "uv-tool":
        return subprocess.run(
            ["uv", "tool", "install", "--force", "prumo-runtime"],
        ).returncode

    if method == "install-script":
        script_path = _download_install_script()
        try:
            print(f"Executando install script de: {CURL_INSTALL_URL}")
            return subprocess.run(["bash", script_path]).returncode
        finally:
            os.unlink(script_path)

    return 1


def _get_post_update_version() -> str | None:
    """Verifica versão instalada após update."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "prumo_runtime", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip().replace("prumo ", "")
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def run_update(args) -> int:
    method_info = detect_install_method()
    remote_version = fetch_remote_version()
    plan = build_update_plan(
        package_manager=method_info["package_manager"],
        current_version=__version__,
        remote_version=remote_version,
        source_kind=method_info["source_kind"],
        launcher=method_info["launcher"],
    )

    payload: dict[str, Any] = {
        "current_version": __version__,
        "remote_version": remote_version,
        "needs_update": plan["needs_update"],
        "channel": UPDATE_CHANNEL,
        "install_method": {
            "launcher": method_info["launcher"],
            "package_manager": method_info["package_manager"],
            "source_kind": method_info["source_kind"],
            "source": method_info["source"],
            "is_editable": method_info["is_editable"],
        },
        "plan": {
            "command": plan["command"],
            "explanation": plan["explanation"],
            "would_execute": False,
        },
    }

    if method_info.get("warning"):
        payload["warning"] = method_info["warning"]

    check_mode = bool(getattr(args, "check", False))
    dry_run = bool(getattr(args, "dry_run", False)) or check_mode
    yes_mode = bool(getattr(args, "yes", False))
    output_format = getattr(args, "format", "text")

    if check_mode or dry_run:
        return _emit(payload, output_format)

    if not plan["needs_update"]:
        return _emit(payload, output_format)

    if plan["command"] is None:
        return _emit(payload, output_format, exit_code=1)

    # Confirmação antes de executar
    if not yes_mode:
        if not _confirm_update(plan, method_info):
            payload["plan"]["aborted"] = True
            return _emit(payload, output_format, exit_code=2)

    # Execução real
    payload["plan"]["would_execute"] = True
    exec_method = plan["command"] if plan["command"] == "install-script" else method_info["package_manager"]
    rc = _execute_plan(plan, exec_method)
    payload["plan"]["executed"] = rc == 0
    payload["plan"]["exit_code"] = rc

    # Pós-update
    if rc == 0:
        new_version = _get_post_update_version()
        workspace_detected = (Path.cwd() / ".prumo").is_dir()
        payload["post_update"] = {
            "new_version": new_version,
            "workspace_detected": workspace_detected,
            "repair_suggested": workspace_detected,
        }

    return _emit(payload, output_format, exit_code=rc)


def _emit(payload: dict, output_format: str, exit_code: int = 0) -> int:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return exit_code

    # Texto humano
    print(f"Runtime atual: {payload['current_version']}")
    if payload["remote_version"] is None:
        print("Versão remota: não verificável (offline ou rede falhou)")
    else:
        print(f"Versão remota: {payload['remote_version']}")
    print(f"Canal: {payload['channel']}")

    im = payload["install_method"]
    print(f"Método: {im['package_manager']} (launcher: {im['launcher']}, fonte: {im['source']})")

    if im["is_editable"]:
        print("⚠ Instalação editable — auto-update desabilitado.")

    if payload.get("warning"):
        print(f"⚠ {payload['warning']}")

    plan = payload["plan"]
    if plan["explanation"]:
        print(f"Plano: {plan['explanation']}")

    if plan.get("aborted"):
        print("Update cancelado pelo usuário.")
    elif plan["command"]:
        if plan.get("would_execute"):
            executed = plan.get("executed")
            exit_code_real = plan.get("exit_code", 0)
            print(f"Comando executado: `{plan['command']}`")
            status = "OK" if executed else f"falhou (exit {exit_code_real})"
            print(f"Resultado: {status}")
        else:
            print(f"Comando que seria executado: `{plan['command']}`")
            print("(use sem --dry-run/--check pra executar)")

    post = payload.get("post_update")
    if post:
        if post.get("new_version"):
            print(f"Versão pós-update: {post['new_version']}")
        if post.get("repair_suggested"):
            print("Workspace detectado no CWD. Rode `prumo repair --workspace .` para alinhar.")

    return exit_code
