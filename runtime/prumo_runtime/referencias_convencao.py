"""Convenção de nome de ficha de fonte em `Referencias/` (#305).

Ficha de fonte segue `Autor_Assunto_AAAA-MM-DD.<ext>` — a mesma regra de
roteamento que o perfil do workspace já usa. O que não casa não é ficha
(operacionais, índices, módulos de procedimento, material solto) e fica fora
da conta de reindexação do índice. A lista fixa de exclusão que esta
convenção substitui vazava: qualquer arquivo novo fora dela virava candidato
a reindexar — no incidente de 03/08, uma auditoria interna, uma pesquisa
autoral e dois operacionais do usuário quase entraram no catálogo.

Módulo folha: só stdlib.
"""

from __future__ import annotations

import re

# Autor (sem underscore) + assunto (pode ter underscore) + data + extensão.
# Dotfiles e rascunhos (`.x`, `_x`) nunca casam: o autor não começa com eles.
# O primeiro caractere é Unicode-aware (Codex, 314-r1): `Álvaro_...` é autor
# legítimo — a convenção documentada não impõe ASCII; só proíbe `.`, `_` e
# espaço na abertura.
FICHA_FILENAME_RE = re.compile(
    r"^[^._\s][^_]*_.+_\d{4}-\d{2}-\d{2}\.[A-Za-z0-9]{1,8}$"
)

# Infraestrutura DO PRODUTO que vive em `Referencias/` — o próprio índice e
# os arquivos de aprendizado que o Prumo cria. Papel distinto da convenção:
# a convenção decide o que É ficha; esta lista marca o que é do produto e
# portanto nunca entra em conta nenhuma (nem candidata, nem "solto"). Fonte
# única — o acervo importa daqui.
INFRAESTRUTURA_PRODUTO = frozenset({"INDICE.md", "EMAIL-CURADORIA.md", "WORKFLOWS.md"})


def is_ficha_filename(name: str) -> bool:
    """O nome declara uma ficha de fonte? Decide só pelo nome — conteúdo não
    entra: a conta do índice roda no runtime, sem abrir arquivo."""
    return bool(FICHA_FILENAME_RE.match(name))
