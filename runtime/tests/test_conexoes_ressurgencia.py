"""
Trava anti-drift das conexões e ressurgência (#148, épico #138).

O hook operacional da regra 17 vive em dois lugares: o garimpo associativo
da revisão semanal (varredura pesada, escrita nos próprios itens com
confirmação verificável) e a ponte única do briefing (fonte restrita ao
já-carregado — zero leitura nova). Este teste trava as três pontas:
weekly-review tem o garimpo, briefing-procedure tem a ponte com teto, e a
regra 17 do core aponta o hook ativo (não diz mais "fica pra depois").
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WEEKLY = (
    REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "weekly-review.md"
)
BRIEFING = (
    REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "briefing-procedure.md"
)
CORE = REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md"


def _rule_17_section(text: str) -> str:
    match = re.search(r"### 17\..*?(?=\n---|\n# )", text, re.S)
    if not match:
        raise AssertionError("regra 17 não encontrada no prumo-core.md")
    return match.group(0)


class ConexoesRessurgenciaTests(unittest.TestCase):
    def test_weekly_review_tem_o_garimpo(self) -> None:
        """Garimpo associativo com confirmação verificável e escrita nos itens."""
        text = WEEKLY.read_text(encoding="utf-8")
        self.assertIn("garimpo", text.lower())
        # Confirmação verificável: arquivo + item + texto exato à vista.
        self.assertIn("texto exato", text.lower())
        # Efeito no acervo declarado.
        self.assertIn("content_hash", text)
        # Trava #97: as conexões moram nos itens, sem índice materializado.
        self.assertIn("índice", text.lower())

    def test_briefing_tem_a_ponte_com_teto(self) -> None:
        """Ponte única junto à proposta do dia, fonte restrita ao já-carregado."""
        text = BRIEFING.read_text(encoding="utf-8")
        self.assertIn("regra 17", text.lower())
        self.assertIn("ponte", text.lower())
        # Fonte barata: o Hibernando da PAUTA é o limbo já carregado.
        self.assertIn("Hibernando", text)
        # Zero leitura nova por causa da ponte.
        self.assertIn("leitura nova", text.lower())

    def test_core_aponta_o_hook_ativo(self) -> None:
        """A regra 17 não diz mais que o hook 'fica pra depois' — aponta onde ele vive."""
        section = _rule_17_section(CORE.read_text(encoding="utf-8"))
        self.assertIn("weekly-review", section)
        self.assertIn("briefing-procedure", section)
        self.assertNotIn(
            "até lá",
            section,
            "a regra 17 ainda trata o hook como futuro — deveria apontar o hook ativo",
        )


if __name__ == "__main__":
    unittest.main()
