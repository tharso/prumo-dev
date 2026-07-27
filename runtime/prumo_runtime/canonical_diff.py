"""Diff do mapa do workspace entre o `AGENT.md` antigo e o regenerado (#247).

O `repair` regenera o canonical do zero quando há drift de versão: caminho que
o usuário tenha adicionado ao `## Mapa do workspace` some com backup silencioso
em `.prumo/backups/` — "backup que ninguém lê é lixo com data" (relatório de
27/07). Este módulo compara os dois mapas por **identidade de path** e devolve
o que sumiu, pro comando avisar nominalmente.

Funções puras (módulo separado por escolha: o `workspace.py` opera no teto de
linhas do baseline). Duas decisões do review do Codex ([P7-1]):

- a identidade é o **primeiro caminho entre crases** do bullet, normalizado —
  release que só muda a DESCRIÇÃO do bullet não dispara nada;
- o resultado descreve o observável ("presente antes, ausente agora"); o runtime
  não sabe dizer se o caminho era autoral ou canônico da versão antiga, e não
  finge saber.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MAP_HEADING = "## Mapa do workspace"
_BULLET_PATH = re.compile(r"^\s*[-*]\s+`([^`]+)`")


def _heading_level(line: str) -> int:
    stripped = line.lstrip()
    return len(stripped) - len(stripped.lstrip("#"))


def extract_map_section(text: str, heading: str = MAP_HEADING) -> str | None:
    """Do heading exato até o próximo heading de nível igual ou superior.

    `None` quando o heading não existe. Heading duplicado: vale a PRIMEIRA
    ocorrência (fail-safe — nunca levanta).
    """
    lines = text.splitlines()
    level = _heading_level(heading)
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i
            break
    if start is None:
        return None
    for j in range(start + 1, len(lines)):
        if lines[j].lstrip().startswith("#") and _heading_level(lines[j]) <= level:
            return "\n".join(lines[start:j])
    return "\n".join(lines[start:])


def map_paths(text: str, heading: str = MAP_HEADING) -> list[str]:
    """Paths (identidade dos bullets) do mapa, na ordem, sem duplicatas.

    Normalização: `./x` → `x`; barra final preservada (`Agente/` é como o mapa
    escreve, e a comparação é entre dois mapas do mesmo formato).
    """
    section = extract_map_section(text, heading)
    if section is None:
        return []
    out: list[str] = []
    for line in section.splitlines():
        m = _BULLET_PATH.match(line)
        if m is None:
            continue
        path = m.group(1).strip()
        if path.startswith("./"):
            path = path[2:]
        if path and path not in out:
            out.append(path)
    return out


@dataclass(frozen=True)
class MapWatch:
    """Snapshot do mapa antes da regeneração + comparação depois.

    Mantém a fiação no `repair_workspace()` em duas linhas — o `workspace.py`
    opera no teto de linhas do baseline ([P7-3] do review).
    """

    path: Path
    before: str

    def dropped(self) -> list[str]:
        if not self.before:
            return []
        after = self.path.read_text(encoding="utf-8") if self.path.is_file() else ""
        return dropped_paths(self.before, after)


def watch(canonical_path: Path) -> MapWatch:
    """Captura o canonical ANTES do move pro backup (depois não há base)."""
    before = canonical_path.read_text(encoding="utf-8") if canonical_path.is_file() else ""
    return MapWatch(canonical_path, before)


def dropped_paths(old_text: str, new_text: str, heading: str = MAP_HEADING) -> list[str]:
    """Paths presentes no mapa antigo e ausentes no novo.

    Mapa antigo sem a seção (arquivo mutilado, template muito velho) devolve
    lista vazia: sem base de comparação não se inventa alarme.
    """
    old = map_paths(old_text, heading)
    if not old:
        return []
    new = set(map_paths(new_text, heading))
    return [p for p in old if p not in new]
