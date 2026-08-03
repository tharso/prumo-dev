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
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from prumo_runtime import __version__
from prumo_runtime.commands.update_sources import (
    _is_valid_runtime_dir,
    _local_dir_from_uv_receipt,
    _staged_version,
)
from prumo_runtime.workspace_paths import LEGACY_FLAT_POST_UPDATE_NOTE, is_legacy_flat_workspace, is_prumo_workspace


REMOTE_VERSION_URL = "https://raw.githubusercontent.com/tharso/prumo/main/VERSION"
DEFAULT_FETCH_TIMEOUT_SECONDS = 2.5
CURL_INSTALL_URL = (
    "https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_runtime_install.sh"
)
UPDATE_CHANNEL = "latest em main"


def _python_supports_update(version_info=None):
    """O update lê TOML (uv-receipt, pyproject) com tomllib, stdlib 3.11+.
    A mínima do runtime é 3.10 (#301): só este comando exige mais que ela,
    então o gate mora aqui e o resto do CLI nunca paga por ele."""
    found = version_info if version_info is not None else sys.version_info
    return (found[0], found[1]) >= (3, 11)


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
    local_source_dir: str | None = None,
    local_install: bool = False,
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

    # Instalação de DIRETÓRIO LOCAL (cache do plugin do host). NÃO vai pro
    # registry: prumo-runtime não é publicado (#170). Vem DEPOIS de editable e
    # install-script (que têm transporte próprio) — só instalações uv-tool
    # locais chegam aqui. Instala do path local da nova versão quando resolvido;
    # senão, erro honesto — nunca um plano que morre no primeiro passo.
    if local_install:
        if local_source_dir:
            plan["uv_target"] = local_source_dir
            plan["command"] = f"uv tool install --force {shlex.quote(local_source_dir)}"
            plan["explanation"] = (
                f"Atualiza runtime de {current_version} pra {remote_version} do "
                f"diretório local {local_source_dir} (a instalação veio do cache do "
                "plugin do host, não do registry)."
            )
        else:
            # Cache sem a versão nova era beco morto (#232, caso real do
            # dono): agora cai no transporte universal — tarball do espelho.
            plan["command"] = "archive"
            plan["archive_installer"] = "uv"
            plan["explanation"] = (
                f"Atualiza runtime de {current_version} pra {remote_version} baixando o "
                "tarball do espelho público (o cache do plugin ainda não tem a versão "
                "nova — o espelho sempre tem)."
            )
        return plan

    # NUNCA registry (#232): prumo-runtime não é publicado no PyPI — o comando
    # falharia hoje e viraria dependency confusion no dia em que alguém
    # registrasse o nome. O transporte é o tarball do espelho, preservando o
    # gerenciador da instalação atual (trocar de gerenciador deixaria o
    # executável velho na frente do PATH).
    if package_manager in ("pip-user", "pipx", "uv-tool"):
        installer = {"pip-user": "pip-user", "pipx": "pipx", "uv-tool": "uv"}[package_manager]
        plan["command"] = "archive"
        plan["archive_installer"] = installer
        plan["explanation"] = (
            f"Atualiza runtime de {current_version} pra {remote_version} baixando o "
            f"tarball do espelho público e reinstalando via {package_manager} "
            "(prumo-runtime não é publicado em registry — o espelho é a fonte)."
        )
    else:
        # Método desconhecido → install-script: ele resolve uv/Python, grava
        # o marker e deixa a instalação em estado conhecido.
        plan["command"] = "install-script"
        plan["explanation"] = (
            f"Método de instalação não detectado — atualiza de {current_version} pra "
            f"{remote_version} re-executando o install script (deixa a instalação em "
            "estado conhecido, com marker)."
        )

    return plan


def resolve_local_source_dir(
    remote_version: str,
    *,
    current_version: str,
    uv_tool_dir: Path | None = None,
    marker_source: str | None = None,
) -> str | None:
    """Resolve o diretório LOCAL da nova versão pra instalação `copy` (uv-tool).

    Fonte agnóstica: o `uv-receipt.toml` do uv registra o `directory` da versão
    ATUAL (ex.: `.../prumo/5.16.0`); derivamos o irmão da versão nova
    (`.../prumo/5.29.0`) e validamos o pyproject. Nunca hardcoda caminho de host
    (#77/#108). `marker_source` é fallback caso o marker guarde um diretório.
    Retorna o path da nova versão, ou None se não for resolvível/válido.
    """
    current_dir = _local_dir_from_uv_receipt(uv_tool_dir)
    if not current_dir and marker_source and Path(marker_source).is_dir():
        current_dir = marker_source
    if not current_dir:
        return None

    # Troca o ÚLTIMO segmento igual à versão atual (opera em Path.parts —
    # cross-platform, não string /-POSIX; não troca ocorrências duplicadas).
    parts = list(Path(current_dir).parts)
    candidate = None
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == current_version:
            parts[i] = remote_version
            candidate = Path(*parts)
            break
    if candidate and _is_valid_runtime_dir(candidate, remote_version):
        return str(candidate)
    return None


def is_local_uv_install(method_info: dict, uv_tool_dir: Path | None = None) -> bool:
    """A instalação atual veio de um DIRETÓRIO LOCAL (cache do plugin), não de
    registry? (#170)

    Detecção robusta, não presa a um marker externo: `source_kind == "copy"` é
    sinal direto; senão, uma instalação `uv-tool` que NÃO é `install-script`
    nem `editable` só pode ter vindo de diretório local — o `prumo-runtime` não
    é publicado em registry —, confirmado pelo `directory` no `uv-receipt.toml`.
    (install-script e editable têm branches próprias e precedência antes desta.)
    """
    if method_info.get("source_kind") == "copy":
        return True
    if (
        method_info.get("package_manager") == "uv-tool"
        and method_info.get("launcher") != "install-script"
        and method_info.get("source_kind") != "editable"
    ):
        return _local_dir_from_uv_receipt(uv_tool_dir) is not None
    return False


def _version_tuple(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


def workspace_core_status(workspace: Path, remote_version: str | None) -> dict | None:
    """Estado do core do workspace ativo vs. a versão pública (#170).

    Update do runtime ≠ update do core do workspace: o core sincroniza via
    `prumo repair` (rodado no pós-update). Este report evita que o `--check`
    esconda um workspace defasado atrás de um runtime em dia. Retorna None se o
    CWD não é um workspace (em qualquer layout, #268)."""
    if not is_prumo_workspace(workspace):
        return None
    try:
        from prumo_runtime.workspace import parse_core_version

        core_v = parse_core_version(workspace)
    except Exception:
        core_v = None
    if not core_v:
        # Versão vazia imprimia `Core do workspace: n/d (em dia)` — ausência virando saúde (Codex, r1).
        return None
    return {
        # No flat a ação é `migrate`, nunca `repair` — sem esta marca o
        # `--check` passaria a recomendar o híbrido (Codex, r4).
        "workspace_layout_legacy_flat": is_legacy_flat_workspace(workspace),
        "workspace_core_version": core_v,
        "workspace_core_needs_update": bool(
            core_v
            and remote_version
            and _version_tuple(core_v) < _version_tuple(remote_version)
        ),
    }


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


ARCHIVE_URL = "https://github.com/tharso/prumo/archive/refs/heads/main.tar.gz"
# Tetos do transporte (#232, review Codex): o tarball real do repo tem ~3 MB
# e ~700 arquivos — os limites são folga de 10x, não calibração fina. Servem
# pra um espelho comprometido/errado não exaurir disco/memória do usuário.
_MAX_ARCHIVE_BYTES = 30 * 1024 * 1024
_MAX_MEMBERS = 8000
_MAX_UNPACKED_BYTES = 150 * 1024 * 1024


def _safe_extract(tar: "tarfile.TarFile", dest: Path) -> None:
    """Extração com preflight PRÓPRIO antes de qualquer extractall (review
    Codex do #232): só diretórios e arquivos regulares (links, devices e
    FIFOs rejeitados — o data_filter do stdlib ainda permite link interno),
    path contido por resolve().relative_to, raiz ÚNICA obrigatória, tetos de
    quantidade e soma descompactada. O data_filter entra DEPOIS, como defesa
    adicional quando existir (3.11.4+)."""
    # Itera com next() em vez de getmembers() (review Codex r2): um
    # metadata-bomb materializaria milhões de TarInfo ANTES do teto.
    members: list[tarfile.TarInfo] = []
    while True:
        member = tar.next()
        if member is None:
            break
        members.append(member)
        if len(members) > _MAX_MEMBERS:
            raise ValueError(f"tarball passou de {_MAX_MEMBERS} membros — abortado")
    dest_resolved = dest.resolve()
    root_part: str | None = None
    total_unpacked = 0
    for member in members:
        if not (member.isdir() or member.isreg()):
            raise ValueError(f"membro não-regular rejeitado (link/device/fifo): {member.name!r}")
        parts = Path(member.name).parts
        if member.name.startswith("/") or ".." in parts or not parts:
            raise ValueError(f"membro suspeito no tarball: {member.name!r}")
        if root_part is None:
            root_part = parts[0]
        elif parts[0] != root_part:
            raise ValueError(
                f"membro fora da raiz única {root_part!r}: {member.name!r}"
            )
        target = dest / member.name
        try:
            target.resolve().relative_to(dest_resolved)
        except ValueError:
            raise ValueError(f"membro fora do destino: {member.name!r}") from None
        total_unpacked += max(member.size, 0)
        if total_unpacked > _MAX_UNPACKED_BYTES:
            raise ValueError("tarball descompactado passa do teto — abortado")
    if getattr(tarfile, "data_filter", None) is not None:
        tar.extractall(dest, members=members, filter="data")
    else:
        tar.extractall(dest, members=members)


def stage_archive_source(remote_version: str, work_dir: Path) -> tuple[str | None, str | None, str | None]:
    """Baixa o tarball do espelho, extrai com filtro e valida o artefato.

    Transporte UNIVERSAL do update (#232): mesma fonte do install-script —
    nunca o registry (prumo-runtime não é publicado; apontar pro PyPI é
    convite a dependency confusion). Retorna (staged_dir, staged_version,
    error): o artefato só é aceito se `pyproject`+`VERSION`+árvore validarem
    e a versão for EXATAMENTE a anunciada pelo plano — mismatch em qualquer
    direção aborta (mais nova = main avançou, rode de novo; mais velha =
    artefato atrasado/inconsistente).

    `PRUMO_UPDATE_ARCHIVE_URL` (env) troca a fonte — usado pelos testes com
    tarball local `file://`; a URL default é HTTPS do espelho.
    """
    url = os.environ.get("PRUMO_UPDATE_ARCHIVE_URL", ARCHIVE_URL)
    if url == ARCHIVE_URL:
        assert url.startswith("https://"), "URL do tarball deve ser HTTPS"
    archive_path = work_dir / "prumo-main.tar.gz"
    try:
        with urllib.request.urlopen(url, timeout=60) as response, archive_path.open("wb") as out:
            # Streaming com teto (review Codex): read() ilimitado deixaria um
            # espelho errado/comprometido exaurir a memória do usuário.
            received = 0
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > _MAX_ARCHIVE_BYTES:
                    return None, None, (
                        f"tarball passou do teto de download ({_MAX_ARCHIVE_BYTES} bytes) — abortado"
                    )
                out.write(chunk)
    except Exception as exc:  # noqa: BLE001 — erro de transporte vira mensagem
        return None, None, f"download do tarball falhou: {exc.__class__.__name__}"
    extract_dir = work_dir / "extracted"
    extract_dir.mkdir()
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            _safe_extract(tar, extract_dir)
    except (tarfile.TarError, ValueError, OSError) as exc:
        return None, None, f"extração do tarball falhou: {exc}"
    roots = [d for d in extract_dir.iterdir() if d.is_dir()]
    if len(roots) != 1:
        return None, None, f"tarball com {len(roots)} raiz(es) — esperado exatamente 1"
    staged_version = _staged_version(roots[0])
    if staged_version is None:
        return None, None, "artefato extraído não é um prumo-runtime válido (pyproject/VERSION/árvore)"
    if staged_version != remote_version:
        # Contrato ESTRITO (review Codex r2): instalar versão diferente da
        # que o plano/oferta anunciou — mesmo que mais nova — é instalar o
        # que o usuário não confirmou.
        if _version_tuple(staged_version) > _version_tuple(remote_version):
            detail = "a versão pública avançou entre a checagem e o download; rode `prumo update` de novo."
        else:
            detail = "o tarball está ATRASADO em relação à versão anunciada — espelho inconsistente; tente de novo mais tarde."
        return None, None, (
            f"tarball traz {staged_version}, mas o plano anunciou {remote_version} — {detail}"
        )
    return str(roots[0]), staged_version, None


def _install_from_dir(source_dir: str, installer: str) -> int:
    """Instala o runtime de um diretório local, preservando o gerenciador da
    instalação atual (#232 — trocar de gerenciador deixaria o executável
    velho na frente do PATH)."""
    if installer == "uv":
        return subprocess.run(["uv", "tool", "install", "--force", source_dir]).returncode
    if installer == "pipx":
        return subprocess.run(["pipx", "install", "--force", source_dir]).returncode
    return subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "--upgrade", source_dir],
    ).returncode


def _execute_plan(plan: dict, method: str) -> tuple[int, str | None]:
    """Executa o plano. Retorna (exit code, versão do ARTEFATO instalado
    quando conhecida) — a validação pós-update compara contra o artefato,
    nunca contra o que o binário diz de si mesmo (review Codex, #232)."""
    if method == "archive":
        remote_version = plan.get("remote_version") or ""
        with tempfile.TemporaryDirectory(prefix="prumo-update-") as tmp:
            staged_dir, staged_version, error = stage_archive_source(
                remote_version, Path(tmp)
            )
            if staged_dir is None:
                print(f"Update abortado: {error}")
                return 1, None
            print(f"Instalando {staged_version} do tarball do espelho ({ARCHIVE_URL})")
            rc = _install_from_dir(staged_dir, plan.get("archive_installer") or "uv")
            return rc, staged_version

    if method == "uv-tool":
        # Instalação de DIRETÓRIO local (cache do plugin) — o alvo mora no
        # plano; nunca um nome de registry (#232).
        target = plan.get("uv_target")
        if not target:
            print("Update abortado: plano uv sem diretório alvo (registry não existe, #232).")
            return 1, None
        return subprocess.run(["uv", "tool", "install", "--force", target]).returncode, plan.get("remote_version")

    if method == "install-script":
        # O script instalava "latest em main" sem contrato — o mesmo bypass
        # do registry em outra roupa (review Codex r4-r5). Staging PRIMEIRO
        # (mesmo preflight e contrato estrito do archive); depois roda o
        # script CONTIDO no artefato validado (a versão do script casa com o
        # artefato — zero download adicional, nem do próprio script) em modo
        # PRUMO_INSTALL_SOURCE_DIR: instala como cópia (nunca editable de um
        # tmp) e grava o marker source_kind=archive.
        remote_version = plan.get("remote_version") or ""
        with tempfile.TemporaryDirectory(prefix="prumo-update-") as tmp:
            staged_dir, staged_version, error = stage_archive_source(
                remote_version, Path(tmp)
            )
            if staged_dir is None:
                print(f"Update abortado: {error}")
                return 1, None
            script_path = Path(staged_dir) / "scripts" / "prumo_runtime_install.sh"
            if not script_path.is_file():
                print("Update abortado: o artefato validado não traz o install script.")
                return 1, None
            print(f"Executando install script do artefato validado ({staged_version})")
            env = {**os.environ, "PRUMO_INSTALL_SOURCE_DIR": staged_dir}
            rc = subprocess.run(["bash", str(script_path)], env=env).returncode
            return rc, staged_version

    return 1, None


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
    if not _python_supports_update():
        print(
            "prumo update requer Python 3.11+ (tomllib na stdlib); este interpretador é "
            f"{sys.version_info[0]}.{sys.version_info[1]}. Os demais comandos do prumo "
            "funcionam normalmente na mínima 3.10.",
            file=sys.stderr,
        )
        return 2
    method_info = detect_install_method()
    remote_version = fetch_remote_version()
    # Instalação de diretório local (cache do plugin): resolve o path da nova
    # versão da fonte agnóstica (uv-receipt), pra não cair no registry
    # inexistente (#170). Detecção não presa a marker externo.
    local_install = is_local_uv_install(method_info)
    local_source_dir = None
    if local_install and remote_version:
        local_source_dir = resolve_local_source_dir(
            remote_version,
            current_version=__version__,
            marker_source=(method_info.get("details") or {}).get("source"),
        )
    plan = build_update_plan(
        package_manager=method_info["package_manager"],
        current_version=__version__,
        remote_version=remote_version,
        source_kind=method_info["source_kind"],
        launcher=method_info["launcher"],
        local_source_dir=local_source_dir,
        local_install=local_install,
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

    # Defasagem do core do WORKSPACE (#170): reportar pra o --check não esconder
    # um workspace defasado atrás de um runtime em dia.
    payload.update(workspace_core_status(Path.cwd(), remote_version) or {})

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
    if plan["command"] == "install-script":
        exec_method = "install-script"
    elif plan["command"] == "archive":
        exec_method = "archive"
    elif plan.get("uv_target"):
        # Instalação via uv de diretório local — o alvo mora no plano.
        exec_method = "uv-tool"
    else:
        exec_method = method_info["package_manager"]
    rc, artifact_version = _execute_plan(plan, exec_method)
    payload["plan"]["executed"] = rc == 0
    payload["plan"]["exit_code"] = rc

    # Pós-update
    if rc == 0:
        new_version = _get_post_update_version()
        # A régua é o ARTEFATO instalado (staged/remota), nunca o que o
        # binário diz de si mesmo — senão um update que não pegou "valida"
        # comparando a versão velha com ela própria (review Codex, #232).
        expected = artifact_version or remote_version
        workspace_detected = is_prumo_workspace(Path.cwd())
        # O repair pós-update GRAVA, e grava nested (`install_skills` força
        # layout_mode="nested"): dispará-lo num flat converteria o layout do
        # usuário como efeito colateral de um update de runtime (#268).
        legacy_flat = is_legacy_flat_workspace(Path.cwd())
        payload["post_update"] = {
            "new_version": new_version,
            "expected_version": expected,
            "version_confirmed": bool(expected) and new_version == expected,
            "workspace_detected": workspace_detected,
            "repair_suggested": workspace_detected and not legacy_flat,
        }
        if legacy_flat:
            payload["post_update"]["workspace_note"] = LEGACY_FLAT_POST_UPDATE_NOTE
        if expected and new_version != expected:
            payload["post_update"]["warning"] = (
                f"binário reporta {new_version}, artefato instalado era {expected} — "
                "PATH pode estar servindo um executável antigo; repair não vai rodar."
            )
        # Propaga o update pro workspace (#146): sem isto, o runtime atualiza
        # mas as skills do workspace ficam velhas e comandos novos "não existem".
        elif workspace_detected and not legacy_flat:
            payload["post_update"].update(
                _run_post_update_repair(Path.cwd(), expected_version=expected)
            )

    return _emit(payload, output_format, exit_code=rc)


def _run_post_update_repair(workspace: Path, *, expected_version: str | None) -> dict:
    """Roda `prumo repair --workspace <ws>` com o binário PÓS-update.

    VERIFICA a versão do binário antes (review Codex, #146): se o `prumo` do
    PATH for outro (pipx/uv/venv antigo), o repair convergiria o workspace pra
    fonte ERRADA — e a poda do install_skills removeria skills novas. Binário
    divergente → não roda, degrada pra sugestão manual.
    """
    exe = shutil.which("prumo")
    if exe is None:
        return {
            "repair_executed": False,
            "repair_note": "binário `prumo` não encontrado no PATH; rode `prumo repair --workspace .` manualmente",
        }
    try:
        version_check = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=15
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return {"repair_executed": False, "repair_note": f"não deu pra verificar o binário do PATH: {exc}"}
    binary_version = version_check.stdout.strip().replace("prumo ", "") if version_check.returncode == 0 else None
    if expected_version is None or binary_version != expected_version:
        return {
            "repair_executed": False,
            "repair_note": (
                f"o `prumo` do PATH ({exe}) está em {binary_version or 'versão desconhecida'}, "
                f"não na recém-instalada {expected_version or '?'} — repair automático abortado "
                "pra não sincronizar o workspace com a fonte errada"
            ),
        }
    try:
        completed = subprocess.run(
            [exe, "repair", "--workspace", str(workspace)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return {"repair_executed": False, "repair_note": f"repair automático falhou: {exc}"}
    return {
        "repair_executed": completed.returncode == 0,
        "repair_exit_code": completed.returncode,
    }


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

    # Core do workspace (#170): não esconder um workspace defasado no texto.
    if "workspace_core_version" in payload:
        core_v = payload["workspace_core_version"] or "n/d"
        if payload.get("workspace_core_needs_update"):
            flat = payload.get("workspace_layout_legacy_flat")
            acao = "`prumo migrate --workspace .` (layout antigo: o repair criaria um híbrido)" if flat else "`prumo repair --workspace .` após atualizar o runtime"
            print(f"⚠ Core do workspace: {core_v} — atrás da pública. Rode {acao}.")
        else:
            print(f"Core do workspace: {core_v} (em dia)")

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
        if post.get("workspace_note"):
            print(f"⚠ {post['workspace_note']}")
        if post.get("repair_executed"):
            print("Workspace detectado no CWD — `prumo repair` executado automaticamente (skills propagadas).")
        elif post.get("repair_suggested"):
            note = post.get("repair_note")
            if note:
                print(f"⚠ {note}")
            print("Workspace detectado no CWD. Rode `prumo repair --workspace .` para alinhar.")

    return exit_code
