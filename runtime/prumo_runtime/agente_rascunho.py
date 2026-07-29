"""Rascunho do agente: território e varredura (#263, P12 do relatório).

No Cowork com ponte de dispositivo, `rm` falha. A #242 fechou isso pro fluxo do
usuário — `_to_delete/`, que ELE esvazia à mão. O que só ficou visível depois:
o agente também não limpa os próprios artefatos, e cada conserto sujava a
quarentena DO USUÁRIO, obrigando o dono a garimpar o que descartou no meio do
que a máquina deixou pra trás.

Módulo próprio porque o `sanitize.py` estava no teto de maior arquivo do gate:
empilhar mais nele custaria contrato em comentário cortado.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from prumo_runtime.scan_primitives import (
    _age_days,
    _rel,
    _tree_has_symlink,
    _usable_root,
    _walk_tree,
)

BACKUP_DIR_NAMES = {"backup", "backups", ".prumo"}


RASCUNHO_RELS = (".prumo/state/rascunho", "_state/rascunho")


def _sob_rascunho(workspace: Path, path: Path) -> bool:
    """Subtree do rascunho é EXCLUSIVA (#263): ordem só garante disjunção
    quando todas as regras rodam."""
    rel = _rel(workspace, path)
    return any(rel == r or rel.startswith(r + "/") for r in RASCUNHO_RELS)


def _arvore_legivel(root: Path) -> bool:
    """`os.walk` engole falha de leitura: subpasta inacessível vira vazia, e
    um arquivo editado hoje sumiria da checagem de frieza enquanto o `move`
    levaria a árvore inteira pelo pai. Falha FECHADA (Codex, r8)."""
    problemas: list[OSError] = []
    for _ in os.walk(root, followlinks=False, onerror=problemas.append):
        pass
    return not problemas


def iter_agente_rascunho(workspace: Path, today: date, ephemeral_days: int) -> list[Path]:
    """Filhos DIRETOS frios do rascunho (#263). A unidade é o filho direto —
    arquivo a arquivo desmontaria reconstrução parcial — e diretório entra só
    com a árvore INTEIRA fria e legível."""
    # Os DOIS roots, como o handover: no flat não existe `.prumo/`.
    frios: list[Path] = []
    filhos: list[Path] = []
    for rel in RASCUNHO_RELS:
        root = workspace / rel
        if not _usable_root(workspace, root):
            continue
        try:
            filhos.extend(sorted(root.iterdir()))
        except OSError:
            continue
    for filho in filhos:
        if filho.is_symlink():
            continue
        if filho.is_file():
            if _age_days(filho, today) > ephemeral_days:
                frios.append(filho)
            continue
        if not filho.is_dir():
            continue
        subdirs, arquivos = _walk_tree(filho)
        # Regra de ouro da #178: mover isto INTEIRO criaria backup dentro de
        # backup. O PRÓPRIO filho entra na checagem — `rascunho/backups/`
        # escapava. Fica onde está; o usuário resolve.
        if any(d.name in BACKUP_DIR_NAMES for d in (filho, *subdirs)):
            continue
        # Symlink faz o `build_plan` recusar depois: contar aqui daria alarme
        # eterno no `/fim` com plano vazio na sanitize (Codex, r5).
        if _tree_has_symlink(filho) or not _arvore_legivel(filho):
            continue
        # TODA a árvore, não só os arquivos: reconstrução criada HOJE com
        # arquivos antigos dentro (um `mv` basta) parecia fria. E sem exigir
        # arquivos, senão carcaça vazia nunca sai.
        tudo = [filho, *subdirs, *arquivos]
        if all(_age_days(x, today) > ephemeral_days for x in tudo):
            frios.append(filho)
    return frios
