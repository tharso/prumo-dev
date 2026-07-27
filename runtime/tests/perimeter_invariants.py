"""Invariantes do perímetro de leitura (#194) — coleção ÚNICA.

Compartilhada por `test_templates.py` (paridade template markdown ↔ gerador
Python ↔ wrappers) e `test_repair.py` (propagação via repair). Cada frase
cobre uma obrigação semântica do desenho acordado na revisão do Codex:
se qualquer representação perder uma delas, o guard quebra.
"""
from __future__ import annotations

PERIMETER_INVARIANTS: tuple[str, ...] = (
    # A seção existe.
    "## Perímetro de leitura",
    # Escopo 1: perímetro automático, sem exploração espontânea.
    "Perímetro automático",
    "Zero exploração espontânea da raiz",
    # Proibição por efeito, não por comando — qualquer ferramenta.
    "Nenhuma enumeração recursiva ou ilimitada",
    "por qualquer ferramenta",
    # Exclusões fixas em qualquer escopo.
    "node_modules",
    "`.git`",
    "caches e builds ficam fora de qualquer listagem",
    # #213: snapshots do próprio Prumo fora de qualquer listagem; .prumo/
    # raso por default (o briefing real listou ~290 entradas de backups).
    "`.prumo/backups/` e `.prumo/backup/` são snapshots, nunca conteúdo de trabalho (#213)",
    "listagem de `.prumo/` é rasa por default",
    # Escopo 2: autorizado pela tarefa — expansão dirigida e rasa.
    "Escopo autorizado pela tarefa",
    "dirigida e rasa",
    "top-level do caminho citado",
    "rastro do alvo",
    "perguntar o caminho, não explorar",
    # Delegação: o perímetro viaja no prompt do subagente, com a proibição
    # explícita de enumerar fora dos caminhos delegados.
    "caminhos permitidos",
    "proibição de enumerar fora deles",
    'Nunca "explore o workspace"',
)


# B4 (relatório de 27/07, decisão do dono): descoberta direta é contrato
# EXCLUSIVO do layout nested — no flat os arquivos do Prumo moram NA raiz.
# Nested contém as três; flat as OMITE preservando a base acima.
NESTED_DISCOVERY_INVARIANTS: tuple[str, ...] = (
    "inclusive na descoberta",
    "as pastas do Prumo são sempre `Prumo/` e `.prumo/`",
    'nunca liste a raiz pra "descobrir o workspace"',
)
