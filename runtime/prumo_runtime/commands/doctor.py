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
a última milha congelada era invisível até 03/08. O elo do workspace (#335)
é o vizinho: o checkout embarcado do CWD comparado com o runtime QUE EXECUTA
este diagnóstico — `workspace.core` mede metadado de versão; conteúdo real
(`workspace.skills`) fica reservado pra #299.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from prumo_runtime import MINIMUM_PYTHON, __version__
from prumo_runtime.commands.store_clone import collect as _collect_store
from prumo_runtime.commands.update import (
    DEFAULT_FETCH_TIMEOUT_SECONDS,
    REMOTE_VERSION_URL,
    fetch_remote_version,
)
from prumo_runtime.workspace_paths import is_legacy_flat_workspace, is_prumo_workspace

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


def _tupla_numerica(v: str | None) -> tuple[int, ...] | None:
    if not v:
        return None
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except ValueError:
        return None


def _sonda_prumo_do_path(runtime_version: str) -> dict:
    """Coerência régua × fonte (#335): a régua é o runtime em execução, mas o
    comando recomendado rodaria o `prumo` do PATH — que pode ser outro (ex.:
    doctor invocado via `PYTHONPATH=<bundle>`). Fonte não coincidente ou não
    verificada nunca é prescrita."""
    exe = shutil.which("prumo")
    if exe is None:
        return {"path_check": "ausente"}
    try:
        sonda = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return {"path_check": "nao_verificado", "path_runtime_version": None}
    if sonda.returncode != 0:
        return {"path_check": "nao_verificado", "path_runtime_version": None}
    versao = sonda.stdout.strip().replace("prumo ", "")
    if versao == runtime_version:
        return {"path_check": "ok"}
    return {"path_check": "divergente", "path_runtime_version": versao}


def _prescreve(comando: str, runtime_version: str) -> dict:
    resultado = _sonda_prumo_do_path(runtime_version)
    resultado["recommended_command"] = comando if resultado["path_check"] == "ok" else None
    return resultado


def _elo_do_workspace(cwd: Path, runtime_version: str) -> dict:
    """O elo do workspace (#335): estado do checkout embarcado do CWD.

    Só reporta — a sonda do PATH roda apenas nos ramos que prescreveriam
    comando; `em_dia`/`indeterminado`/ausente não pagam subprocesso."""
    if not is_prumo_workspace(cwd):
        return {"detected": False}
    if is_legacy_flat_workspace(cwd):
        # Precedência de layout: no flat a comparação não ocorre — a ação é
        # migrate (#268/#170), nunca repair.
        bloco = {"detected": True, "layout": "flat", "status": "legacy_flat"}
        bloco.update(_prescreve("prumo migrate --workspace .", runtime_version))
        return bloco
    try:
        from prumo_runtime.workspace import parse_core_version

        core_v = parse_core_version(cwd)
    except Exception:
        core_v = None
    core: dict = {"version": core_v, "runtime_version": runtime_version}
    tupla_core = _tupla_numerica(core_v)
    tupla_runtime = _tupla_numerica(runtime_version)
    if tupla_core is None or tupla_runtime is None:
        # Ausente, vazio ou malformado: nunca direção inventada.
        core["status"] = "indeterminado"
    elif tupla_core == tupla_runtime:
        core["status"] = "em_dia"
    else:
        core["status"] = "divergente"
        if tupla_core < tupla_runtime:
            core["direction"] = "core_behind_runtime"
            core.update(_prescreve("prumo repair --workspace .", runtime_version))
        else:
            # Codex 335-code-r1 (P1): repair converge pro runtime em execução —
            # com core à frente, prescrevê-lo seria DOWNGRADE do workspace.
            core["direction"] = "core_ahead_of_runtime"
            core.update(_prescreve("prumo update", runtime_version))
    return {"detected": True, "layout": "nested", "core": core}


def _sufixo_prescricao(bloco: dict, acao: str) -> str:
    comando = bloco.get("recommended_command")
    if comando:
        return f"rode `{comando}`"
    check = bloco.get("path_check")
    if check == "ausente":
        return f"`prumo` ausente do PATH — runtime-paths.md passo 0 antes de {acao}"
    if check == "divergente":
        return (
            f"`prumo` do PATH está em {bloco.get('path_runtime_version')} — alinhe o PATH "
            f"com este runtime, ou reexecute o diagnóstico por ele, antes de {acao}"
        )
    return f"binário do PATH não verificado — confira antes de {acao}"


def _linha_do_workspace(bloco: dict) -> str:
    if not bloco.get("detected"):
        return "nenhum no diretório atual"
    if bloco.get("status") == "legacy_flat":
        return f"layout flat (legado) — {_sufixo_prescricao(bloco, 'migrar')}"
    core = bloco["core"]
    versao = core.get("version") or "?"
    runtime = core["runtime_version"]
    if core["status"] == "em_dia":
        return f"core {versao} — em dia com o runtime deste diagnóstico"
    if core["status"] == "indeterminado":
        return "core sem versão legível — estado indeterminado"
    if core["direction"] == "core_behind_runtime":
        return (
            f"core {versao} — DEFASADO (runtime deste diagnóstico: {runtime}); "
            f"{_sufixo_prescricao(core, 'reparar')}"
        )
    return (
        f"core {versao} — à frente do runtime deste diagnóstico ({runtime}), "
        f"provável runtime velho; {_sufixo_prescricao(core, 'atualizar')}"
    )


def run_doctor(args) -> int:
    timeout = getattr(args, "network_timeout", DEFAULT_FETCH_TIMEOUT_SECONDS)
    remote = _fetch_remote(timeout)
    store = _collect_store(remote_version=remote)
    # Elo LOCAL (#335): core do CWD × runtime em execução — não depende de rede.
    workspace = _elo_do_workspace(Path.cwd(), __version__)
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
        "workspace": workspace,
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
        f"  workspace: {_linha_do_workspace(workspace)}\n"
        f"  executável neste interpretador: sim (este diagnóstico é a prova)"
    )
    return 0
