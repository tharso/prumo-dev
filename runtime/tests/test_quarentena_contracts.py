"""Guards textuais do contrato de quarentena (#242).

Remover do inbox = MOVER (quarentena `_to_delete/` ou destino durável), nunca
deletar. Estes guards congelam as frases que carregam o contrato nos módulos —
se alguém reintroduzir deleção real como via, ou apagar a máquina de remoção,
o CI acusa antes do drift virar comportamento.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "skills"
INBOX = SKILLS / "prumo" / "references" / "modules" / "inbox-processing.md"
CORE = SKILLS / "prumo" / "references" / "prumo-core.md"
PROTECTION = SKILLS / "prumo" / "references" / "file-protection-rules.md"
FAXINA = SKILLS / "prumo" / "references" / "modules" / "faxina.md"
HIGIENE = SKILLS / "higiene" / "SKILL.md"
ALLOWLIST = SKILLS / "decidir" / "references" / "acoes-allowlist.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class QuarentenaContractsTest(unittest.TestCase):
    def test_inbox_processing_nao_tem_delecao_como_via(self) -> None:
        text = _read(INBOX)
        self.assertNotIn(
            "deletar o original do inbox com ação real de filesystem",
            text,
            "deleção real voltou como operação válida (#242 revertida)",
        )
        self.assertNotIn(
            "solicitar a permissão do runtime",
            text,
            "o degrau beco-sem-saída do fallback voltou (#242)",
        )

    def test_inbox_processing_tem_maquina_de_remocao(self) -> None:
        text = _read(INBOX)
        for marker in (
            "### Máquina de remoção (por item, nesta ordem)",
            "_to_delete/<AAAA-MM-DD>_<escopo>/",
            "REMOCAO_FALHOU",
            "mover, nunca deletar",
            "Retenção durável",
            "### Sequência de arquivamento (retenção)",
        ):
            self.assertIn(marker, text, f"contrato da máquina de remoção sem: {marker!r}")

    def test_core_assert_usa_remover_nao_deletar(self) -> None:
        text = _read(CORE)
        self.assertIn(
            "ASSERT: Antes de remover item de inbox, confirmar com o usuário o plano único de commit.",
            text,
        )
        self.assertNotIn("Antes de deletar item de inbox", text)

    def test_quarentena_e_do_usuario(self) -> None:
        """`_to_delete/` fora de listagem/índice/contagem — e o Prumo nunca esvazia."""
        protection = _read(PROTECTION)
        self.assertIn("`_to_delete/` (raiz do workspace)", protection)
        self.assertIn("Quarentena do USUÁRIO (#242)", protection)
        self.assertIn("nem esvazia", protection)
        inbox = _read(INBOX)
        self.assertIn("nunca lista, indexa,\n   conta ou esvazia", inbox)

    def test_faxina_sinaliza_e_higiene_resolve(self) -> None:
        """#212 mantida: faxina só sinaliza; a oferta confirmável mora na higiene."""
        faxina = _read(FAXINA)
        self.assertIn("apenas sinalizar", faxina)
        self.assertIn("mora na `higiene` (#242)", faxina)
        higiene = _read(HIGIENE)
        self.assertIn("processados inconsistentes", higiene)
        self.assertIn("Movo pra quarentena `_to_delete/`", higiene)
        self.assertIn("não recebe backup duplicado", higiene)

    def test_allowlist_separa_quarentena_de_retencao(self) -> None:
        text = _read(ALLOWLIST)
        self.assertIn("Remover nunca é deletar (#242)", text)
        self.assertIn("movem o próprio arquivo pro destino durável", text)

    def test_nenhuma_skill_recomenda_delecao_real_do_inbox(self) -> None:
        """Varredura: nenhum contrato em skills/ traz deleção real do inbox como via."""
        offenders = []
        for md in SKILLS.rglob("*.md"):
            if "deletar o original do inbox" in _read(md):
                offenders.append(str(md.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [], f"deleção real do inbox reapareceu em: {offenders}")


if __name__ == "__main__":
    unittest.main()
