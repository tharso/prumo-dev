"""Instalação (e poda) das skills base no workspace.

Extraído de `workspace.py` (#146) — o arquivo estava no teto do baseline do
quality gate, mesmo precedente da extração do `pauta_parsing.py` (#122).
`workspace.py` re-exporta `install_skills`, então os importadores existentes
seguem funcionando.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from prumo_runtime.constants import repo_root_from


def install_skills(workspace: Path, *, layout_mode: str = "nested") -> list[str]:
    """Copia as skills base do repo pra `.prumo/skills/` do workspace.

    Sincroniza de verdade (#146): além de copiar as atuais, PODA as que
    sumiram da fonte — sem isso, skill deletada do produto (ex.: `start`)
    ficava pra sempre no workspace e nos hosts. Só toca `.prumo/skills/`
    (infra); skills do usuário moram em `Prumo/Custom/skills/`. Entradas
    ocultas (dotfiles) não são skills — ficam.
    """
    from prumo_runtime.workspace_paths import workspace_paths as ws_paths

    paths = ws_paths(workspace, layout_mode=layout_mode)
    if not paths.nested_layout:
        return []
    repo = repo_root_from(Path(__file__))
    if repo is None:
        # Em wheel install, repo_root_from cai no fallback _bundled/. Se mesmo
        # assim retornou None, é estado patológico (wheel sem _bundled, ou
        # execução fora de contexto). Retorna lista vazia em vez de crashar.
        return []
    source = repo / "skills"
    if not source.is_dir():
        return []
    target = paths.system_skills_root
    installed: list[str] = []
    for skill_dir in sorted(source.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        dest = target / skill_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_dir, dest)
        installed.append(skill_dir.name)

    if target.is_dir():
        current = set(installed)
        for entry in sorted(target.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if entry.name not in current:
                shutil.rmtree(entry)
    return installed
