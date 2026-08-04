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
sem quebrar contrato. A checagem do clone da store (#324) já mora aqui:
a última milha congelada era invisível até 03/08.
"""
from __future__ import annotations

import json
import platform
import shutil
import sys
import time

from prumo_runtime import MINIMUM_PYTHON, __version__
from prumo_runtime.commands.store_clone import collect as _collect_store
from prumo_runtime.commands.update import (
    DEFAULT_FETCH_TIMEOUT_SECONDS,
    REMOTE_VERSION_URL,
    fetch_remote_version,
)

SCHEMA = "prumo_doctor_host.v1"


def _fetch_remote(timeout: float) -> str | None:
    """Uma ida só ao VERSION público, COM cache-busting (#291 — o CDN já
    mentiu duas vezes): serve de sonda de rede E de referência pro clone da
    store. No host que motivou o comando (VM do Cowork) a resposta é 403 no
    túnel — degrada pra None, nunca pra traceback."""
    return fetch_remote_version(
        url=f"{REMOTE_VERSION_URL}?cb={int(time.time())}", timeout=timeout
    )


def _linha_da_store(retrato: dict) -> str:
    if not retrato.get("found"):
        return "sem clone da store neste host"
    versao = retrato.get("version") or "?"
    idade = retrato.get("fetch_age_days")
    idade_txt = f"último fetch há {idade:g}d" if idade is not None else "sem fetch registrado"
    status = retrato.get("status")
    if status == "fresca":
        return f"clone {versao} — em dia com o remoto"
    if status == "indeterminada":
        return f"clone {versao}, {idade_txt} — sem rede pra comparar"
    remoto = retrato.get("remote_version") or "?"
    return (
        f"clone {versao}, {idade_txt} — DEFASADA (remoto {remoto}); "
        f"re-sync do marketplace no app; `prumo update` cobre o runtime"
    )


def run_doctor(args) -> int:
    timeout = getattr(args, "network_timeout", DEFAULT_FETCH_TIMEOUT_SECONDS)
    remote = _fetch_remote(timeout)
    store = _collect_store(remote_version=remote)
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
        "network": "ok" if remote is not None else "blocked",
        "remote_version": remote,
        "store_clone": store,
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
        f"  store   : {_linha_da_store(store)}\n"
        f"  executável neste interpretador: sim (este diagnóstico é a prova)"
    )
    return 0
