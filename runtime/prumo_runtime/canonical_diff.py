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
# CommonMark aceita `-`, `*` e `+` como marcador de lista: aceitar só dois
# faria uma entrada autoral legítima sumir sem aviso (Codex, diff r1).
_BULLET_PATH = re.compile(r"^\s*[-*+]\s+`([^`]+)`")


def _heading_level(line: str) -> int:
    stripped = line.lstrip()
    return len(stripped) - len(stripped.lstrip("#"))


def extract_map_sections(text: str, heading: str = MAP_HEADING) -> list[str]:
    """TODAS as seções com esse heading, cada uma até o próximo heading de
    nível igual ou superior.

    Heading duplicado devolve as duas: ignorar a segunda esconderia justamente
    o caminho que sumiu — airbag que escolhe não abrir (Codex, diff r1).
    Nunca levanta: texto sem o heading devolve lista vazia.
    """
    lines = text.splitlines()
    level = _heading_level(heading)
    out: list[str] = []
    starts = [i for i, line in enumerate(lines) if line.strip() == heading]
    for start in starts:
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if lines[j].lstrip().startswith("#") and _heading_level(lines[j]) <= level:
                end = j
                break
        out.append("\n".join(lines[start:end]))
    return out


def _normalize(raw: str) -> str:
    """Identidade real do path: sem `./`, sem barra final, separador único.

    `Escrita/` e `Escrita` são o mesmo caminho — tratá-los como identidades
    diferentes faria uma mudança de formatação do template afirmar perda que
    não houve (Codex, diff r1).
    """
    path = raw.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.rstrip("/")


def map_paths(text: str, heading: str = MAP_HEADING) -> list[str]:
    """Paths (identidade dos bullets) do mapa, na ordem, sem duplicatas —
    unindo TODAS as seções homônimas."""
    out: list[str] = []
    for section in extract_map_sections(text, heading):
        for line in section.splitlines():
            m = _BULLET_PATH.match(line)
            if m is None:
                continue
            path = _normalize(m.group(1))
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
