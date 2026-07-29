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

import hashlib
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


def _tree_has_symlink(path: Path) -> bool:
    """True se o próprio path ou QUALQUER descendente é symlink. Candidato
    assim nunca entra no plano; se o link surgir depois da aprovação, a
    revalidação na fronteira da mutação bloqueia."""
    if path.is_symlink():
        return True
    if not path.is_dir():
        return False
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        base = Path(dirpath)
        for name in dirnames + filenames:
            if (base / name).is_symlink():
                return True
    return False


def _size_bytes(path: Path) -> int:
    if path.is_symlink() or path.is_file():
        return path.lstat().st_size
    _, files = _walk_tree(path)
    return sum(p.lstat().st_size for p in files)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _content_id(workspace: Path, path: Path) -> str:
    """Identidade forte do candidato pro fingerprint do plano.

    Arquivo → SHA-256 do conteúdo. Diretório → SHA-256 de um manifesto
    determinístico da árvore (path relativo, tipo, tamanho, mtime_ns e
    hash de conteúdo por arquivo) — mudou qualquer coisa lá dentro, muda a
    identidade e o apply bloqueia."""
    if path.is_file() and not path.is_symlink():
        return _sha256(path)
    dirs, files = _walk_tree(path)
    # `mtime_ns` do DIRETÓRIO também (#263): a elegibilidade depende dele.
    lines = [f"{p.relative_to(path).as_posix()}|d|{p.lstat().st_mtime_ns}" for p in dirs]
    lines += [
        f"{p.relative_to(path).as_posix()}|f|{p.lstat().st_size}|{p.lstat().st_mtime_ns}|{_sha256(p)}"
        for p in files
    ]
    manifest = "\n".join(sorted(lines))
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest()
