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

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _safe_target(workspace: Path, rel: str) -> Path:
    """Resolve `rel` dentro de `workspace`, recusando path absoluto ou `..`.

    O harness aplica operações destrutivas (delete); um cenário mal escrito com
    `/etc/...` ou `../../` não pode escapar do tmpdir.
    """
    ws = workspace.resolve()
    target = (workspace / rel).resolve()
    if target != ws and ws not in target.parents:
        raise ValueError(f"op de replay tenta sair do workspace: {rel!r}")
    return target


def _safe_parent(workspace: Path, rel: str) -> Path:
    """Valida `rel` pelo diretório-PAI, sem resolver o componente final.

    Para `move` (#242): `.resolve()` no componente final seguiria um symlink
    terminal — e mover um link significa mover o LINK, nunca o alvo. O pai é
    normalizado (tem de ficar dentro do workspace); o último componente fica
    como está, inspecionável via `lstat`/`is_symlink`.
    """
    ws = workspace.resolve()
    raw = workspace / rel
    parent = raw.parent.resolve()
    if parent != ws and ws not in parent.parents:
        raise ValueError(f"op de replay tenta sair do workspace: {rel!r}")
    return parent / raw.name


def apply_replay(workspace: Path, ops: list[dict], *, allow_delete: bool = True) -> list[dict]:
    """Aplica operações de filesystem gravadas e devolve o TRACE (ops aplicadas).

    Ops suportadas (o mínimo pra representar o que os cenários exercem):
    - {"op": "write", "path": ..., "content": ...}  — escreve/sobrescreve
    - {"op": "append", "path": ..., "content": ...} — anexa
    - {"op": "delete", "path": ...}                  — remove arquivo
    - {"op": "mkdir", "path": ...}                   — cria diretório
    - {"op": "move", "path": ..., "dest": ...}       — move (nunca sobrescreve;
      symlink terminal é movido como link, não o alvo)

    `allow_delete=False` simula o host sem deleção (a ponte do Cowork, #242):
    op `delete` levanta `PermissionError` — prova que um fluxo compliant não
    depende de deleção. O trace retornado preserva a ordem e é a base da parte
    de trace do oráculo do C5 (discrimina `move` de `delete` + recriação, que
    produzem o mesmo estado final).
    """
    trace: list[dict] = []
    for op in ops:
        kind = op["op"]
        if kind == "move":
            src = _safe_parent(workspace, op["path"])
            if not src.exists() and not src.is_symlink():
                raise ValueError(f"origem de move inexistente: {op['path']!r}")
            dest = _safe_parent(workspace, op["dest"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() or dest.is_symlink():
                raise ValueError(f"destino de move já existe: {op['dest']!r}")
            src.rename(dest)
            trace.append(op)
            continue
        target = _safe_target(workspace, op["path"])
        if kind == "write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(op["content"], encoding="utf-8")
        elif kind == "append":
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as fh:
                fh.write(op["content"])
        elif kind == "delete":
            if not allow_delete:
                raise PermissionError(
                    f"host sem deleção: op delete bloqueada ({op['path']!r})"
                )
            if target.exists():
                target.unlink()
        elif kind == "mkdir":
            target.mkdir(parents=True, exist_ok=True)
        else:  # pragma: no cover - guarda contra op inválida em cenário mal escrito
            raise ValueError(f"op de replay desconhecida: {kind!r}")
        trace.append(op)
    return trace


def provision_skills(workspace: Path) -> str:
    """Instala as skills DESTA cópia do repo no workspace de teste, pinadas.

    Sem isso, o agente real usaria as skills globais/stale do host (ou nenhuma)
    e a cadência mediria outra versão. Copia `skills/` do repo para
    `<ws>/.prumo/skills/` e grava um marcador com a versão sob teste, pra o
    relatório dizer o que foi medido. Devolve a versão.
    """
    dst = workspace / ".prumo" / "skills"
    shutil.copytree(REPO_ROOT / "skills", dst, dirs_exist_ok=True)
    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    marker = workspace / ".prumo" / "PRUMO-VERSION"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(version + "\n", encoding="utf-8")
    return version


def run_claude_code(workspace: Path, user_input: str, *, timeout_s: int = 300) -> dict:
    """Invoca o agente real via `claude -p` no diretório do workspace.

    Retorna um dict com stdout/stderr/returncode. **Quem chama DEVE checar o
    returncode** — se o `claude` falhar (401, timeout, ausente), o workspace
    fica intocado e rodar o oráculo em cima disso vira falso verde. O stdout
    (stream-json) guarda o transcript e os eventos de tool_use — base do oráculo
    `transcript estrutural`/`tool-call` (C10) que entra em A1.

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
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"returncode": 124, "stdout": "", "stderr": f"timeout após {timeout_s}s"}
    except FileNotFoundError:
        return {"returncode": 127, "stdout": "", "stderr": "binário `claude` não encontrado no PATH"}
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
