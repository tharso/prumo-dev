"""`prumo seed` — materializa a semente do briefing em arquivo (#216, opção b).

No Cowork o runtime é inalcançável por topologia (VM isolada, spike #205):
o transporte da semente lá era leitura direta — funcional, mas pagando o
custo integral (50–63k tokens medidos no briefing real de 25/07). Este
comando fecha o buraco: o runtime DA MÁQUINA LOCAL grava o `local_panorama`
em `.prumo/state/local-panorama.json`, e o agente do Cowork LÊ o arquivo
(~poucos KB) em vez de reler as fontes.

Contrato de consumo (Passo 3 do briefing-procedure.md):
- gate por CAPACIDADE (schema + `outras_secoes` presente), como na semente
  viva;
- frescor POR FONTE: `source_mtimes` carrega o mtime de cada fonte NO
  MOMENTO da geração — o consumidor compara com os mtimes atuais (listagem
  plana barata) e faz fallback direto SÓ da fonte que mudou;
- o agente NUNCA escreve este arquivo (é estado do runtime, #214).

Quem roda: o dono/agente local com runtime (manual, `/fim` sugerindo, ou
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
from prumo_runtime.local_panorama import build_local_panorama
from prumo_runtime.workspace import build_config_from_existing
from prumo_runtime.workspace_paths import workspace_paths

SEED_SCHEMA_VERSION = "prumo_local_panorama_file.v1"
SEED_FILENAME = "local-panorama.json"


def _mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(
            timespec="seconds"
        )
    except OSError:
        return None


def build_seed_payload(workspace: Path) -> dict:
    """Monta o payload do arquivo-semente. Leitura pura das fontes (a mesma
    montagem do `local_panorama` do briefing, #197/#206) — a única escrita
    deste comando é o próprio artefato."""
    workspace = workspace.expanduser().resolve()
    config = build_config_from_existing(workspace)
    paths = workspace_paths(workspace)
    today = datetime.now(ZoneInfo(config.timezone_name)).date()
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
    )
    return {
        "schema_version": SEED_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workspace_path": str(workspace),
        "local_panorama": panorama,
        "payload_completeness": completeness,
        # Frescor POR FONTE: o consumidor compara com os mtimes atuais
        # (listagem plana) — fonte que mudou depois da geração cai no
        # fallback direto; as demais seguem servidas pelo arquivo.
        "source_mtimes": {
            "pauta": _mtime_iso(paths.pauta),
            "inbox": _mtime_iso(paths.inbox),
            "registro": _mtime_iso(paths.registro),
            "processed": _mtime_iso(paths.inbox_processed),
            "inbox4mobile_newest": (preview.get("freshness") or {}).get(
                "newest_inbox_mtime"
            ),
        },
    }


def seed_file_path(workspace: Path) -> Path:
    return workspace.expanduser().resolve() / ".prumo" / "state" / SEED_FILENAME


def write_seed(workspace: Path) -> Path:
    """Grava o artefato atomicamente (mkstemp + replace — sem meia-semente
    visível nem `.tmp` previsível)."""
    payload = build_seed_payload(workspace)
    target = seed_file_path(workspace)
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
    if not (workspace / ".prumo").is_dir():
        print(f"workspace sem `.prumo/`: {workspace} — nada a semear aqui.")
        return 1
    target = write_seed(workspace)
    payload = json.loads(target.read_text(encoding="utf-8"))
    sections = payload["local_panorama"]["pauta"]["sections"]
    outras = payload["local_panorama"]["pauta"]["outras_secoes"]
    total = sum(s["count"] for s in sections) + sum(s["count"] for s in outras)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"[seed] semente gravada em `{target.relative_to(workspace)}` — "
            f"{total} item(ns) da PAUTA ({len(sections)} seções canônicas + "
            f"{len(outras)} autorais), gerada em {payload['generated_at']}."
        )
    return 0
