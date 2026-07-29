"""`prumo seed` — materializa a semente do briefing em arquivo (#216, opção b).

No Cowork o runtime é inalcançável por topologia (VM isolada, spike #205):
o transporte da semente lá era leitura direta — funcional, mas pagando o
custo integral (50–63k tokens medidos no briefing real de 25/07). Este
comando fecha o buraco: o runtime DA MÁQUINA LOCAL grava o `local_panorama`
em `.prumo/state/local-panorama.json`, e o agente do Cowork LÊ o arquivo
(~poucos KB) em vez de reler as fontes.

Contrato de consumo (Passo 3 do briefing-procedure.md) — gate TRIPLO:
1. capacidade (schema + `outras_secoes` presente), como na semente viva;
2. DATA: `local_panorama.generated_for` == hoje no fuso do workspace —
   `visible_today` e sinais de faxina dependem da data, não só dos
   arquivos (virada do dia invalida);
3. frescor POR FONTE: `source_mtimes` + `inbox4mobile_manifest` carregam o
   retrato de cada fonte NO MOMENTO da geração — o consumidor compara com
   o estado atual (listagem plana barata) e faz fallback direto SÓ da
   fonte que mudou.

Integridade do snapshot: os mtimes (em ns) são capturados ANTES da
montagem e revalidados DEPOIS — fonte editada no meio da geração dispara
um retry único; persistindo, o comando aborta em vez de gravar uma
semente costurada de dois instantes.

O agente NUNCA escreve este arquivo (é estado do runtime, #214). Quem
roda: o dono/agente local com runtime (manual, `/fim` sugerindo, ou
launchd — agendamento é operação da máquina, não deste comando).
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.constants import repo_root_from
from prumo_runtime.inbox_preview import load_inbox_preview
from prumo_runtime import faxina_thresholds
from prumo_runtime.local_panorama import build_local_panorama
from prumo_runtime.curated import render_report, snapshot_curated
from prumo_runtime.indice_integridade import render as render_indice
from prumo_runtime.workspace import build_config_from_existing
from prumo_runtime.workspace_paths import (
    is_legacy_flat_workspace,
    is_prumo_workspace,
    legacy_flat_refusal,
    workspace_paths,
)

SEED_SCHEMA_VERSION = "prumo_local_panorama_file.v1"
SEED_FILENAME = "local-panorama.json"

_OPERATIONAL_NAMES = {"inbox-preview.html"}


class SeedError(RuntimeError):
    """Erro controlado do seed (vira exit 2 no CLI, sem traceback)."""


def _mtime_iso(mtime_ns: int) -> str:
    return datetime.fromtimestamp(mtime_ns / 1e9, tz=timezone.utc).isoformat(
        timespec="seconds"
    )


def _stat_entry(path: Path) -> dict | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return {"mtime": _mtime_iso(st.st_mtime_ns), "mtime_ns": st.st_mtime_ns}


def _inbox4mobile_manifest(inbox_dir: Path) -> list[dict]:
    """Manifesto RASO e determinístico do Inbox4Mobile: nome, tamanho e
    mtime de cada arquivo (índice do preview incluso; symlinks fora).
    Só o `mais novo` não basta — adicionar/remover/renomear um arquivo que
    não é o mais novo passaria invisível. Falha de listagem ou de stat é
    ERRO VISÍVEL — manifesto parcial com cara de íntegro mente."""
    if not inbox_dir.is_dir() or inbox_dir.is_symlink():
        return []
    try:
        children = sorted(inbox_dir.iterdir(), key=lambda p: p.name)
    except OSError as exc:
        raise SeedError(
            f"listagem do Inbox4Mobile falhou ({exc}) — semente não gravada"
        ) from exc
    import stat as stat_module

    entries: list[dict] = []
    for entry in children:
        if entry.name in _OPERATIONAL_NAMES:
            continue
        # Um único lstat protegido classifica E data — is_symlink/is_file
        # separados poderiam falhar fora do try e virar exclusão silenciosa.
        try:
            st = entry.lstat()
        except OSError as exc:
            raise SeedError(
                f"stat falhou em Inbox4Mobile/{entry.name} ({exc}) — "
                "manifesto parcial mentiria; semente não gravada"
            ) from exc
        if stat_module.S_ISLNK(st.st_mode) or not stat_module.S_ISREG(st.st_mode):
            continue
        entries.append(
            {
                "name": entry.name,
                "size": st.st_size,
                "mtime": _mtime_iso(st.st_mtime_ns),
                "mtime_ns": st.st_mtime_ns,
            }
        )
    return entries


def _referencias_manifest(root: Path) -> list[dict]:
    """Manifesto raso das fichas: nome + tamanho + mtime. Só o mtime da PASTA
    não bastaria — editar uma ficha não mexe no diretório, e a decisão do
    índice depende do conjunto (#261)."""
    if not root.is_dir() or root.is_symlink():
        return []
    import stat as stat_module

    try:
        filhos = sorted(root.iterdir(), key=lambda p: p.name)
    except OSError as exc:
        raise SeedError(
            f"listagem de Referencias/ falhou ({exc}) — semente não gravada"
        ) from exc
    entradas: list[dict] = []
    for entry in filhos:
        if entry.suffix.lower() != ".md":
            continue
        try:
            st = entry.lstat()
        except OSError as exc:
            raise SeedError(
                f"stat falhou em Referencias/{entry.name} ({exc}) — "
                "manifesto parcial mentiria; semente não gravada"
            ) from exc
        if stat_module.S_ISLNK(st.st_mode) or not stat_module.S_ISREG(st.st_mode):
            continue
        entradas.append(
            {"name": entry.name, "size": st.st_size, "mtime_ns": st.st_mtime_ns}
        )
    return entradas


def _capture_sources(paths) -> dict:
    """Retrato COMPLETO das fontes num instante — inclui o manifesto do
    Inbox4Mobile: captura antes/depois só protege o que ela enxerga."""
    return {
        "pauta": _stat_entry(paths.pauta),
        "inbox": _stat_entry(paths.inbox),
        "registro": _stat_entry(paths.registro),
        "processed": _stat_entry(paths.inbox_processed),
        "inbox4mobile": _inbox4mobile_manifest(paths.inbox4mobile_root),
        # #258: o override de thresholds é FONTE — sem ele aqui, editar
        # `Custom/rules/faxina-thresholds.md` depois do `prumo seed` deixaria
        # a semente "fresca" transportando número velho (Codex, diff r1).
        "faxina_override": _stat_entry(
            paths.custom_rules_root / "faxina-thresholds.md"
        ),
        # #261: sem isto, o índice podia ser TRUNCADO depois do `prumo seed` e
        # a semente seguiria "fresca" carregando `decisao: ok` — o incidente
        # reencenado com JSON e gravata (Codex, 261D-1). O manifesto cobre
        # `INDICE.md` junto com as fichas: ele é um `.md` de `Referencias/`, e
        # um `_stat_entry` separado pra ele seria linha que nenhuma mutação
        # distingue (achado da bateria).
        "referencias": _referencias_manifest(paths.referencias_root),
    }


def _build_once(workspace: Path, paths, timezone_name: str) -> dict:
    today = datetime.now(ZoneInfo(timezone_name)).date()
    preview = load_inbox_preview(
        workspace, repo_root_from(Path(__file__)), allow_regen=False
    )
    panorama, completeness = build_local_panorama(
        pauta_path=paths.pauta,
        inbox_path=paths.inbox,
        registro_path=paths.registro,
        processed_path=paths.inbox_processed,
        preview=preview,
        today=today,
        thresholds=faxina_thresholds.effective(workspace),  # #258
        referencias_root=paths.referencias_root,  # #261
        indice_path=paths.referencias_index,
    )
    return {
        "schema_version": SEED_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workspace_path": str(workspace),
        "local_panorama": panorama,
        "payload_completeness": completeness,
    }


def build_seed_payload(workspace: Path) -> dict:
    """Monta o payload com snapshot ÍNTEGRO: mtimes capturados antes e
    revalidados depois da montagem; fonte editada no meio → retry único;
    persistindo, aborta (semente costurada de dois instantes mente)."""
    workspace = workspace.expanduser().resolve()
    config = build_config_from_existing(workspace)
    paths = workspace_paths(workspace)

    for attempt in (1, 2):
        before = _capture_sources(paths)
        payload = _build_once(workspace, paths, config.timezone_name)
        after = _capture_sources(paths)
        if before == after:
            payload["inbox4mobile_manifest"] = after.pop("inbox4mobile")
            payload["source_mtimes"] = after
            return payload
        if attempt == 2:
            raise SeedError(
                "fontes mudaram durante a geração da semente (duas tentativas) — "
                "rode de novo num momento quieto; nada foi gravado"
            )
    raise AssertionError("unreachable")


def seed_file_path(workspace: Path) -> Path:
    return workspace.expanduser().resolve() / ".prumo" / "state" / SEED_FILENAME


def _require_clean_target(workspace: Path, target: Path) -> None:
    """Cerca da escrita (#189, mesmo padrão do sanitize): nenhum componente
    de workspace→target pode ser symlink — escrever "pra dentro" de um link
    gravaria fora do território."""
    probe = workspace
    for part in target.relative_to(workspace).parts:
        probe = probe / part
        if probe.is_symlink():
            raise SeedError(
                f"`{probe.relative_to(workspace)}` é symlink — escrita recusada, "
                "nada foi gravado"
            )


def write_seed(workspace: Path) -> Path:
    """Grava o artefato atomicamente (mkstemp + replace — sem meia-semente
    visível nem `.tmp` previsível), com cadeia de escrita sem symlink."""
    workspace = workspace.expanduser().resolve()
    payload = build_seed_payload(workspace)
    target = seed_file_path(workspace)
    _require_clean_target(workspace, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(target.parent), prefix=SEED_FILENAME + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return target


def run_seed(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    if not is_prumo_workspace(workspace):
        print(f"não parece um workspace do Prumo: {workspace} — nada a semear aqui.")
        return 1
    # `seed` só existe pra GRAVAR (semente + snapshot dos curados), e ambos os
    # destinos são `.prumo/` literal. Não há metade read-only pra salvar aqui.
    if is_legacy_flat_workspace(workspace):
        print(legacy_flat_refusal(workspace, "semear"))
        return 1
    # Snapshot dos curados (#262). Fica AQUI, e não dentro de
    # `build_seed_payload`, porque construtor de payload não ganha escrita
    # surpresa. Esta é a rota do Cowork (#216) — o host onde o incidente de
    # 27/07 aconteceu e que um gancho só no briefing deixaria descoberto.
    snapshot = snapshot_curated(workspace)
    try:
        target = write_seed(workspace)
    except SeedError as exc:
        print(f"[seed] {exc}")
        return 2
    payload = json.loads(target.read_text(encoding="utf-8"))
    sections = payload["local_panorama"]["pauta"]["sections"]
    outras = payload["local_panorama"]["pauta"]["outras_secoes"]
    total = sum(s["count"] for s in sections) + sum(s["count"] for s in outras)
    if getattr(args, "format", "text") == "json":
        # Relatório VAI NO PAYLOAD: texto solto antes do JSON tornaria o stdout
        # imparseável exatamente no incidente que ele denuncia (Codex, 262D-6).
        payload["curated_snapshot"] = snapshot
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        aviso = render_report(snapshot)
        if aviso:
            print(aviso)
        indice = render_indice(payload.get("local_panorama", {}).get("indice_referencias", {}))
        if indice:
            print(f"[indice] {indice}")
        print(
            f"[seed] semente gravada em `{target.relative_to(workspace)}` — "
            f"{total} item(ns) da PAUTA ({len(sections)} seções canônicas + "
            f"{len(outras)} autorais), válida pra {payload['local_panorama']['generated_for']}, "
            f"gerada em {payload['generated_at']}."
        )
    return 0
