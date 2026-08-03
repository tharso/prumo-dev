"""
Comando `prumo doctor --host` — o diagnóstico do host numa chamada (#309).

O incidente do tomllib (#301) custou ~7 chamadas de investigação na unha:
sistema, Python, rede, presença e executabilidade do runtime, cada um por
sonda própria. Este comando responde tudo de uma vez — e o fato de ele
RODAR já é a prova de executabilidade do runtime neste interpretador,
inclusive do embarcado quando invocado com
`PYTHONPATH=<bundle> python3 -m prumo_runtime doctor --host`.

O modo `--host` é explícito: deixa espaço pros diagnósticos da #299
(divergência bundle × `.prumo/skills`) entrarem no mesmo comando depois,
sem quebrar contrato.
"""
from __future__ import annotations

import json
import platform
import shutil
import sys
import urllib.error
import urllib.request

from prumo_runtime import MINIMUM_PYTHON, __version__
from prumo_runtime.commands.update import DEFAULT_FETCH_TIMEOUT_SECONDS, REMOTE_VERSION_URL

SCHEMA = "prumo_doctor_host.v1"


def _probe_network(timeout: float) -> str:
    """`ok` | `blocked`. Uma ida barata ao VERSION público; no host que
    motivou o comando (VM do Cowork) a resposta é 403 no túnel — degrada
    pra `blocked`, nunca pra traceback."""
    try:
        with urllib.request.urlopen(REMOTE_VERSION_URL, timeout=timeout):
            return "ok"
    except (urllib.error.URLError, OSError, ValueError):
        return "blocked"


def run_doctor(args) -> int:
    timeout = getattr(args, "network_timeout", DEFAULT_FETCH_TIMEOUT_SECONDS)
    payload = {
        "schema": SCHEMA,
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": "%d.%d.%d" % sys.version_info[:3],
        "python_executable": sys.executable,
        "minimum_python": "%d.%d" % MINIMUM_PYTHON,
        "python_ok": sys.version_info[:2] >= MINIMUM_PYTHON,
        "runtime_version": __version__,
        # Se este código está rodando, o runtime executa NESTE interpretador —
        # é o campo que teria respondido "o embarcado roda aqui?" em uma chamada.
        "executable_here": True,
        "runtime_on_path": shutil.which("prumo"),
        "network": _probe_network(timeout),
    }
    if getattr(args, "format", "text") == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    rede = "ok" if payload["network"] == "ok" else "bloqueada"
    no_path = payload["runtime_on_path"] or "ausente do PATH (ver runtime-paths.md passo 0)"
    print(
        f"prumo {__version__} — diagnóstico do host\n"
        f"  sistema : {payload['os']}\n"
        f"  python  : {payload['python']} (mínima {payload['minimum_python']}"
        f"{', ok' if payload['python_ok'] else ' — ABAIXO DA MÍNIMA'})\n"
        f"  rede    : {rede}\n"
        f"  prumo   : {no_path}\n"
        f"  executável neste interpretador: sim (este diagnóstico é a prova)"
    )
    return 0
