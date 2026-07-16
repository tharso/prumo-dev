"""Registro dos guardrails ASSERT do core (#178, épico #177).

O critério 6 do épico manda MOVER material pra fase, nunca deletar guardrail.
Este teste congela o conjunto exato dos `ASSERT:` do core: sumiu um, mudou o
texto ou entrou um novo → o CI acusa e a mudança precisa ser consciente
(atualizar o registro aqui é parte do diff revisável).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md"

_ASSERT_LINE = re.compile(r"^`(ASSERT:.*)`\s*$", re.MULTILINE)

# Registro canônico — texto exato dos 12 ASSERTs (v5.33.x). Mudança aqui é
# decisão, não acidente: atualize junto com o core e explique no PR.
EXPECTED_ASSERTS = {
    "ASSERT: Usar Gmail MCP e Calendar MCP como fonte primária de email e calendário.",
    "ASSERT: Se existir Prumo/Inbox4Mobile/_preview-index.json, linkar inbox-preview.html antes de abrir qualquer arquivo bruto.",
    "ASSERT: Antes de deletar item de inbox, confirmar com o usuário o plano único de commit.",
    "ASSERT: Registrar no Prumo/REGISTRO.md antes de remover o original do inbox.",
    "ASSERT: Na primeira resposta do briefing, é proibido abrir arquivo bruto de Prumo/Inbox4Mobile/*.",
    (
        "ASSERT: No update aplicado à mão (sem runtime), a allowlist de escrita é apenas "
        ".prumo/system/PRUMO-CORE.md e .prumo/backups/<scope>/<timestamp>/... — via runtime, "
        "os destinos são os gerenciados do repair (#146: .prumo/skills/, adapters, "
        "Prumo/AGENT.md com backup e wrappers via mescla in-place). Arquivos PESSOAIS do "
        "usuário são proibidos nos dois caminhos."
    ),
    "ASSERT: Antes do panorama do briefing, o sistema deve tentar preflight de versão e avisar quando detectar versão nova.",
    "ASSERT: Se Prumo/VERSION local for maior que prumo_version do workspace, o briefing deve acusar core defasado antes de seguir.",
    "ASSERT: Arquivo frio só pode ser movido para archive se houver entrada correspondente em .prumo/state/archive/ARCHIVE-INDEX.*",
    (
        'ASSERT: Toda entrada em .prumo/state/archive/ARCHIVE-INDEX.* registra paths relativos '
        'ao workspace (ex: "PAUTA.md", ".prumo/state/old.md"). Nunca paths absolutos com '
        '"/Users/..." ou "C:\\...". Paths absolutos em estado persistido violam o contrato de '
        "portabilidade do workspace e são bug."
    ),
    "ASSERT: Prumo/Agente/PERFIL.md nunca entra em autosanitização; higiene só acontece com confirmação explícita do usuário.",
    "ASSERT: Pendência viva, registro resolvido e histórico não devem disputar espaço em Prumo/Agente/PERFIL.md como se fossem a mesma espécie de informação.",
}


def _extract_asserts(text: str) -> set[str]:
    return {" ".join(match.split()) for match in _ASSERT_LINE.findall(text)}


class CoreAssertsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.found = _extract_asserts(CORE.read_text(encoding="utf-8"))
        cls.expected = {" ".join(item.split()) for item in EXPECTED_ASSERTS}

    def test_asserts_count_is_12(self) -> None:
        self.assertEqual(
            len(self.found),
            12,
            f"o core deveria ter 12 ASSERTs; achei {len(self.found)} — "
            "guardrail removido/adicionado sem atualizar o registro",
        )

    def test_asserts_set_matches_registry(self) -> None:
        missing = self.expected - self.found
        unexpected = self.found - self.expected
        self.assertFalse(
            missing, f"ASSERT(s) sumiram ou mudaram de texto no core: {sorted(missing)}"
        )
        self.assertFalse(
            unexpected,
            f"ASSERT(s) novos/alterados fora do registro: {sorted(unexpected)} — "
            "atualize EXPECTED_ASSERTS conscientemente no mesmo PR",
        )


if __name__ == "__main__":
    unittest.main()
