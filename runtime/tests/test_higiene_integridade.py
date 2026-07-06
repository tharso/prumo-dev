"""Trava do check de integridade referencial da higiene (#95).

O eixo de órfãos e cross-refs quebradas estava descoberto: a higiene cobria
contradição e staleness, mas não integridade referencial (referência que aponta
pra nada, coisa mencionada que nunca ganhou página). Este guard trava que o
check existe, cobre os quatro tipos do #95, mantém a natureza detecta-e-propõe
da higiene, e carrega o limite anti-zelo (estilo pessoal não é erro).
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HIGIENE = REPO_ROOT / "skills" / "higiene" / "SKILL.md"


class HigieneIntegridadeTests(unittest.TestCase):
    def _text(self) -> str:
        return HIGIENE.read_text(encoding="utf-8")

    def test_check_integridade_existe(self) -> None:
        text = self._text().lower()
        self.assertIn("integridade referencial", text)
        # Os dois eixos do #95: órfãos e referências quebradas.
        self.assertRegex(text, r"órf(ã|a)")
        self.assertTrue(
            "quebrad" in text or "aponta pra lugar nenhum" in text,
            "o check precisa nomear referência quebrada / que aponta pra nada",
        )

    def test_cobre_os_quatro_tipos(self) -> None:
        text = self._text().lower()
        # 1) tag sem área definida no PERFIL
        self.assertIn("perfil", text)
        self.assertIn("tag", text)
        # 2) pessoa órfã em PESSOAS.md
        self.assertIn("pessoas.md", text)
        # 3) referência quebrada a arquivo em Referencias/
        self.assertIn("referencias/", text)
        # 4) projeto/área sem página (README)
        self.assertTrue(
            "readme" in text or "sem página" in text,
            "o check precisa cobrir projeto/área sem página correspondente",
        )

    def test_mantem_natureza_detecta_e_propoe(self) -> None:
        text = self._text().lower()
        # Higiene propõe, nunca conserta sozinha.
        self.assertIn("propor", text)
        # Anti-zelo: ausência de convenção / estilo pessoal não é erro.
        self.assertIn("não é erro", text)

    def test_fluxo_roda_os_oito_checks(self) -> None:
        # O fluxo de execução não pode parar em 7 e deixar o check novo órfão.
        self.assertIn("(1-8)", self._text())


if __name__ == "__main__":
    unittest.main()
