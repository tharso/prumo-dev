"""`prumo projetos [--sync]` — índice de projetos com pulso puxado (#201).

Sem `--sync`: ZERO acesso aos projetos externos — só lê o `PROJETOS.md`
persistido e reporta. Com `--sync`: coleta o pulso dos caminhos registrados
e escreve APENAS o `PROJETOS.md` (transacional; estrutura inválida = zero
escrita). Exit codes: 0 completo, 1 sync parcial (erros por projeto no
report), 2 estrutura inválida.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from prumo_runtime.projetos import (
    SCHEMA_VERSION,
    build_readonly_report,
    sync_index_text,
    write_atomically,
)


def _index_path(workspace: Path) -> Path:
    return workspace / "Prumo" / "Agente" / "PROJETOS.md"


def _print(report: dict, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print(f"[projetos] {SCHEMA_VERSION}")
    for project in report.get("projects", []):
        bits = [project.get("name", "?")]
        if project.get("path"):
            bits.append(project["path"])
        if project.get("staleness"):
            bits.append(f"frescor: {project['staleness']}")
        if project.get("error"):
            bits.append(f"ERRO: {project['error']}")
        print("[projetos]   " + " | ".join(bits))
    for error in report.get("errors", []):
        print(f"[projetos] erro: {error}")


def run_projetos(args: argparse.Namespace) -> int:
    workspace = Path(getattr(args, "workspace", None) or ".").expanduser().resolve()
    fmt = getattr(args, "format", "text") or "text"
    now = datetime.now(timezone.utc)
    index = _index_path(workspace)
    if not index.exists():
        _print(
            {
                "schema_version": SCHEMA_VERSION,
                "projects": [],
                "errors": [f"índice não encontrado: {index}"],
            },
            fmt,
        )
        return 2

    # read_bytes preserva CRLF — o modo texto traduziria e a regravação
    # mudaria bytes autorais fora dos blocos (Codex diff r1).
    text = index.read_bytes().decode("utf-8")
    if not getattr(args, "sync", False):
        report = build_readonly_report(text, now=now)
        _print(report, fmt)
        return 2 if report["structural"] else 0

    new_text, report = sync_index_text(
        text, home=Path.home(), workspace=workspace, now=now
    )
    if new_text is None:
        _print(report, fmt)
        return 2
    if new_text != text:
        write_atomically(index, new_text)
    _print(report, fmt)
    return 1 if report["errors"] else 0
