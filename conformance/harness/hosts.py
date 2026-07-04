"""Hosts — como o cenário é "executado" sobre um workspace.

Dois adapters:

- `replay` — determinístico, SEM LLM. Aplica um conjunto de operações de
  filesystem pré-gravadas (o que um agente *compliant* ou *violation* faria).
  É o host que roda em CI: prova que o pipeline (setup → executa → captura →
  oráculo) funciona e que o oráculo discrimina certo/errado, sem custo nem
  flakiness de modelo.

- `claude_code` — invoca o agente real via `claude -p` (headless). É o host da
  cadência (semanal/pré-release), rodado pelo dono num shell autenticado. NÃO
  roda em CI: custa tokens, é não-determinístico (é justamente o que se mede) e
  precisa de credencial — a invocação aninhada dentro de outra sessão de agente
  falha com 401 (verificado em 2026-07-04). Ver SPEC.md → "Rodando de verdade".
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def apply_replay(workspace: Path, ops: list[dict]) -> None:
    """Aplica operações de filesystem gravadas. Usado pelo host `replay`.

    Ops suportadas (o mínimo pra representar o que os cenários exercem):
    - {"op": "write", "path": ..., "content": ...}  — escreve/sobrescreve
    - {"op": "append", "path": ..., "content": ...} — anexa
    - {"op": "delete", "path": ...}                  — remove arquivo
    - {"op": "mkdir", "path": ...}                   — cria diretório
    """
    for op in ops:
        kind = op["op"]
        target = workspace / op["path"]
        if kind == "write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(op["content"], encoding="utf-8")
        elif kind == "append":
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as fh:
                fh.write(op["content"])
        elif kind == "delete":
            if target.exists():
                target.unlink()
        elif kind == "mkdir":
            target.mkdir(parents=True, exist_ok=True)
        else:  # pragma: no cover - guarda contra op inválida em cenário mal escrito
            raise ValueError(f"op de replay desconhecida: {kind!r}")


def run_claude_code(workspace: Path, user_input: str, *, timeout_s: int = 300) -> dict:
    """Invoca o agente real via `claude -p` no diretório do workspace.

    Retorna um dict com stdout/returncode. O contrato é verificado pelo oráculo
    sobre o filesystem depois; o stdout (stream-json) guarda o transcript e os
    eventos de tool_use — a base do oráculo `transcript estrutural` (C10) que
    entra em A1.

    Não é chamado em CI (ver docstring do módulo). Requer um shell autenticado.
    """
    cmd = [
        "claude",
        "-p",
        user_input,
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "bypassPermissions",
        "--add-dir",
        str(workspace),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
