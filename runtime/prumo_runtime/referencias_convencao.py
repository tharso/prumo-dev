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
FICHA_FILENAME_RE = re.compile(
    r"^[A-Za-z0-9][^_]*_.+_\d{4}-\d{2}-\d{2}\.[A-Za-z0-9]{1,8}$"
)


def is_ficha_filename(name: str) -> bool:
    """O nome declara uma ficha de fonte? Decide só pelo nome — conteúdo não
    entra: a conta do índice roda no runtime, sem abrir arquivo."""
    return bool(FICHA_FILENAME_RE.match(name))
