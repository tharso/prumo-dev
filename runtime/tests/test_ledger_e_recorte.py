"""Âncoras dos contratos #303 (baixa no ledger) e #306 (recorte delimitado).

Guards anti-regressão pedidos no review do PR #315 (Codex, r2): sem eles,
remover a frase de qualquer um dos módulos deixaria a suite verde e o
contrato desapareceria em silêncio — a categoria que o repo chama de
manutenção morta ao contrário.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestBaixaNoLedger(unittest.TestCase):
    """#303: a ordem é move → verificação → baixa, nos campos reais do schema."""

    def setUp(self):
        self.text = (REPO_ROOT / "skills" / "decidir" / "SKILL.md").read_text(
            encoding="utf-8"
        )

    def test_verificacao_antes_da_baixa(self):
        """A ORDEM é o contrato (Codex, 315-r3): presença das frases não basta
        — a verificação tem de vir textualmente ANTES da baixa, com o
        'somente então' entre elas."""
        move = self.text.find("executar o move do original")
        verificacao = self.text.find("verificar origem ausente e destino íntegro")
        somente_entao = self.text.find("somente então")
        baixa = self.text.find("atualizar a entrada no `_processed.json`")
        for pos, nome in (
            (move, "move"),
            (verificacao, "verificação"),
            (somente_entao, "somente então"),
            (baixa, "baixa"),
        ):
            self.assertGreater(pos, -1, f"elo ausente: {nome}")
        self.assertLess(move, verificacao)
        self.assertLess(verificacao, somente_entao)
        self.assertLess(somente_entao, baixa)
        self.assertIn("Verificação falhou → não dar baixa", self.text)

    def test_campos_do_contrato_do_ledger(self):
        """`status + rodada` era campo inventado (Codex, 315-r2): o schema
        real do `_processed.json` tem filename/processed_at/status/reason."""
        self.assertIn("`filename`, `processed_at`, `status`", self.text)
        self.assertNotIn("status + rodada", self.text)


class TestRecorteDelimitado(unittest.TestCase):
    """#306: a regra é o recorte, não a ferramenta — com fallback sem shell."""

    def setUp(self):
        self.text = (
            REPO_ROOT
            / "skills"
            / "prumo"
            / "references"
            / "modules"
            / "load-policy.md"
        ).read_text(encoding="utf-8")

    def test_regra_do_recorte_com_fallback_sem_shell(self):
        self.assertIn("Arquivo grande não entra inteiro (#306)", self.text)
        self.assertIn("leitura DELIMITADA pelas APIs do host", self.text)
        self.assertIn("a regra é o recorte, não a ferramenta", self.text)


if __name__ == "__main__":
    unittest.main()
