"""Primitivas de varredura symlink-safe da `sanitize` (#263).

Extraídas quando o `sanitize.py` passou o teto de maior arquivo do quality
gate ao ganhar a família `agente_rascunho`. A catraca do codebase só anda num
sentido, e a exceção regrada vale só pra rota do briefing — então a saída é
seam, não pedido de exceção.

O seam é honesto: aqui mora a mecânica de ENXERGAR o disco com segurança
(cadeia sem symlink, travessia que nunca segue link, idade por `lstat`); no
`sanitize.py` fica o que DECIDIR fazer com o que foi enxergado. Módulo folha:
só stdlib.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path


def _rel(workspace: Path, path: Path) -> str:
    return path.relative_to(workspace).as_posix()


def _age_days(path: Path, today: date) -> int:
    return (today - date.fromtimestamp(path.lstat().st_mtime)).days


def _mtime_ns(path: Path) -> int:
    return path.lstat().st_mtime_ns


def _walk_tree(root: Path) -> tuple[list[Path], list[Path]]:
    """(dirs, files) sob `root`, ordem determinística, symlinks NUNCA
    seguidos nem listados (`os.walk(followlinks=False)` + filtro)."""
    dirs: list[Path] = []
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for name in sorted(dirnames):
            child = base / name
            if child.is_symlink():
                dirnames.remove(name)
                continue
            dirs.append(child)
        dirnames.sort()
        for name in sorted(filenames):
            child = base / name
            if not child.is_symlink():
                files.append(child)
    return dirs, files


def _clean_chain(workspace: Path, path: Path) -> bool:
    """True se nem `path` nem nenhum ancestral até o workspace é symlink.

    Toda operação (listar no plano, ler, hashear, mover, apagar) exige cadeia
    limpa: um diretório symlinkado no meio do caminho redireciona a operação
    pra fora do território real — recusar é mais barato que auditar.
    """
    try:
        rel = path.relative_to(workspace)
    except ValueError:
        return False
    current = workspace
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            return False
    return True


def _usable_root(workspace: Path, root: Path) -> bool:
    """Root só é enumerável se existe, é diretório real e tem cadeia limpa —
    validado ANTES de qualquer is_dir/walk (root symlinkado não é nem
    atravessado pra descobrir filhos)."""
    return _clean_chain(workspace, root) and not root.is_symlink() and root.is_dir()
