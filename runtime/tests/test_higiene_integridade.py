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

    @staticmethod
    def _problemas_de_numeracao(texto: str) -> list[str]:
        """Função pura pra o guard poder ser provado com entrada sintética.
        Contra o arquivo REAL (que está correto) nenhuma mutação do código o
        faria falhar — guard sem fixture negativa é decoração (achado da
        bateria de mutação)."""
        import re as _re
        ids = [int(m) for m in _re.findall(r"^### (\d+)\. ", texto, _re.M)]
        problemas = []
        if ids != sorted(set(ids)):
            problemas.append(f"heading repetido ou fora de ordem: {ids}")
        elif ids != list(range(1, len(ids) + 1)):
            problemas.append(f"numeração das detecções tem buraco: {ids}")
        if ids and f"(1-{ids[-1]})" not in texto:
            problemas.append(f"fluxo não cobre até a detecção {ids[-1]}")
        return problemas

    def test_fluxo_roda_todos_os_checks(self) -> None:
        self.assertEqual(self._problemas_de_numeracao(self._text()), [])

    def test_o_guard_pega_secao_removida_do_meio(self) -> None:
        """Olhar só o MAIOR heading deixava passar remoção do meio: apagar a
        seção 8 e manter a 9 preservava `(1-9)` e o guard ficava verde
        (Codex, 261D-7)."""
        sintetico = "### 1. a\n### 2. b\n### 9. c\n\n1. Rodar todos os checks (1-9)\n"
        self.assertTrue(self._problemas_de_numeracao(sintetico))

    def test_o_guard_pega_heading_duplicado(self) -> None:
        sintetico = "### 1. a\n### 1. b\n\n1. Rodar todos os checks (1-1)\n"
        self.assertTrue(self._problemas_de_numeracao(sintetico))

    def test_o_guard_pega_fluxo_curto(self) -> None:
        sintetico = "### 1. a\n### 2. b\n\n1. Rodar todos os checks (1-1)\n"
        self.assertTrue(self._problemas_de_numeracao(sintetico))

    def test_o_guard_aceita_numeracao_correta(self) -> None:
        """Negativa da negativa: entrada boa não pode reprovar."""
        sintetico = "### 1. a\n### 2. b\n\n1. Rodar todos os checks (1-2)\n"
        self.assertEqual(self._problemas_de_numeracao(sintetico), [])


if __name__ == "__main__":
    unittest.main()
