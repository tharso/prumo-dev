"""
Comando `prumo update` — atualiza o runtime instalado.

Detecta como o runtime foi instalado (pip vs curl install script) via marker
JSON em `~/.local/share/prumo/install-method.json`. Sem marker, faz fallback
explícito (tenta pip primeiro). Sempre suporta `--dry-run` e `--check` pra
hosts/agentes consumirem sem efeito colateral.

Issue de origem: #86. Naming `update` (não `upgrade`) por sugestão do Codex —
"update" é gesto cotidiano leve, "upgrade" carrega peso semântico de migração
maior. `prumo upgrade` é alias de compatibilidade.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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
INSTALL_METHOD_MARKER_RELATIVE = "prumo/install-method.json"


def install_marker_path() -> Path:
    """
    Localização do marker JSON que registra o método de instalação.

    Unix: $XDG_DATA_HOME/prumo/install-method.json (default: ~/.local/share/prumo/)
    Windows: %LOCALAPPDATA%/prumo/install-method.json
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "prumo" / "install-method.json"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "prumo" / "install-method.json"


def detect_install_method(marker_path: Path | None = None) -> dict[str, Any]:
    """
    Detecta como o runtime foi instalado.

    Retorna dict com:
        method: "pip" | "curl" | "unknown"
        source: "marker" | "fallback"
        details: dados extras (path do marker, saída de pip show, etc.)

    Estratégia:
    1. Se marker existir e for legível, retorna método declarado.
    2. Sem marker, tenta `pip show prumo-runtime`. Se sucesso, "pip" via fallback.
    3. Senão, "unknown" via fallback (caller decide o que fazer).
    """
    target = marker_path if marker_path is not None else install_marker_path()
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            method = data.get("method", "unknown")
            return {
                "method": method if method in ("pip", "curl") else "unknown",
                "source": "marker",
                "details": data,
            }
        except (json.JSONDecodeError, OSError):
            # Marker corrompido — cai no fallback
            pass

    # Fallback: tenta pip show
    pip_executable = shutil.which("pip") or shutil.which("pip3")
    if pip_executable:
        try:
            result = subprocess.run(
                [pip_executable, "show", "prumo-runtime"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return {
                    "method": "pip",
                    "source": "fallback",
                    "details": {"reason": "pip show prumo-runtime succeeded"},
                }
        except (subprocess.SubprocessError, OSError):
            pass

    return {
        "method": "unknown",
        "source": "fallback",
        "details": {
            "reason": "no marker found and pip show prumo-runtime failed or unavailable",
        },
    }


def fetch_remote_version(
    url: str = REMOTE_VERSION_URL,
    timeout: float = DEFAULT_FETCH_TIMEOUT_SECONDS,
) -> str | None:
    """
    Busca versão remota do runtime.

    Retorna string da versão (ex: `"5.3.0"`) ou None se rede falhar.
    Falha graciosa: caller decide o que fazer com None (provavelmente avisar
    "não foi possível verificar versão remota" e seguir).
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8").strip()
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def build_update_plan(
    method: str,
    current_version: str,
    remote_version: str | None,
) -> dict[str, Any]:
    """
    Monta plano de update baseado no método de instalação.

    Retorna dict com:
        current_version, remote_version, needs_update, command, explanation.

    Se `remote_version is None`, `needs_update=False` e `command=None`
    (caller decide se reporta erro ou apenas avisa offline).
    """
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

    plan["needs_update"] = True

    if method == "pip":
        plan["command"] = "pip install --upgrade prumo-runtime"
        plan["explanation"] = (
            f"Atualiza runtime de {current_version} pra {remote_version} via pip."
        )
    elif method == "curl":
        plan["command"] = f"bash <(curl -fsSL {CURL_INSTALL_URL})"
        plan["explanation"] = (
            f"Atualiza runtime de {current_version} pra {remote_version} re-executando "
            "o install script."
        )
    else:
        plan["command"] = None
        plan["explanation"] = (
            "Método de instalação não detectado. Reinstale manualmente via pip "
            "(`pip install --upgrade prumo-runtime`) ou via install script "
            f"(`bash <(curl -fsSL {CURL_INSTALL_URL})`)."
        )

    return plan


def run_update(args) -> int:
    """
    Handler do comando `prumo update`. Suporta `--check`, `--dry-run`, `--format`.

    Sem flags, **executa update real**. Em CI ou ambientes automatizados, sempre
    usar `--dry-run` ou `--check`.
    """
    method_info = detect_install_method()
    remote_version = fetch_remote_version()
    plan = build_update_plan(
        method=method_info["method"],
        current_version=__version__,
        remote_version=remote_version,
    )

    payload: dict[str, Any] = {
        "current_version": __version__,
        "remote_version": remote_version,
        "needs_update": plan["needs_update"],
        "install_method": method_info["method"],
        "install_method_source": method_info["source"],
        "plan": {
            "command": plan["command"],
            "explanation": plan["explanation"],
            "would_execute": False,
        },
    }

    check_mode = bool(getattr(args, "check", False))
    dry_run = bool(getattr(args, "dry_run", False)) or check_mode

    output_format = getattr(args, "format", "text")

    if check_mode:
        # `--check` reporta versão remota e plano sem executar nem checar mais nada
        return _emit(payload, output_format)

    if dry_run:
        return _emit(payload, output_format)

    if not plan["needs_update"]:
        return _emit(payload, output_format)

    if plan["command"] is None:
        # Método unknown — não executa, instrui usuário
        return _emit(payload, output_format, exit_code=1)

    # Execução real do update
    payload["plan"]["would_execute"] = True
    rc = _execute_plan(plan, method_info["method"])
    payload["plan"]["executed"] = rc == 0
    payload["plan"]["exit_code"] = rc
    return _emit(payload, output_format, exit_code=rc)


def _execute_plan(plan: dict, method: str) -> int:
    """Executa o comando do plano. Retorna exit code."""
    if method == "pip":
        # Usar `pip install --upgrade` do mesmo Python que está rodando o runtime
        return subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "prumo-runtime"],
        ).returncode
    if method == "curl":
        # Re-executa o install script via shell. Requer bash + curl.
        return subprocess.run(
            ["bash", "-c", f"bash <(curl -fsSL {CURL_INSTALL_URL})"],
        ).returncode
    return 1


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
    print(f"Método de instalação: {payload['install_method']} ({payload['install_method_source']})")
    if payload["plan"]["explanation"]:
        print(f"Plano: {payload['plan']['explanation']}")
    if payload["plan"]["command"]:
        if payload["plan"].get("would_execute"):
            executed = payload["plan"].get("executed")
            exit_code_real = payload["plan"].get("exit_code", 0)
            print(f"Comando executado: `{payload['plan']['command']}`")
            status = "OK" if executed else f"falhou (exit {exit_code_real})"
            print(f"Resultado: {status}")
        else:
            print(f"Comando que seria executado: `{payload['plan']['command']}`")
            print("(use sem `--dry-run` nem `--check` pra executar de verdade)")

    return exit_code
