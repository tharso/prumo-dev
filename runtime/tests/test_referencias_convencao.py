"""Convenção de ficha de fonte (#305) — os casos reais do incidente de 03/08.

A semente mandou reindexar 4 arquivos que não são ficha de fonte; a lista
fixa de exclusão não os conhecia. A convenção decide pelo nome, e estes
testes fixam os dois lados da régua com os nomes reais do workspace.
"""

import unittest

from prumo_runtime.referencias_convencao import is_ficha_filename


class TestFichasReais(unittest.TestCase):
    def test_ficha_na_convencao_casa(self):
        for nome in (
            "Karpathy_Software-3.0_2026-04-10.md",
            "Anthropic_Claude-Code-Best-Practices_2026-03-01.md",
            "Autor_Assunto_com_underscores_2026-01-01.md",
            "Autor_Paper_2026-01-01.pdf",
            "Álvaro_Assunto_2026-01-01.md",
        ):
            self.assertTrue(is_ficha_filename(nome), nome)

    def test_os_quatro_do_incidente_ficam_fora(self):
        """Nenhum destes é ficha de fonte de terceiro — indexá-los sujaria a
        biblioteca (relatório de campo de 03/08, F-4)."""
        for nome in (
            "CONTEXT-EFFICIENCY-AUDIT.md",
            "Frila-StripePartners-GHz-due-diligence-2026-07-04.md",
            "REUNIOES-INDEX.md",
            "WORKFLOWS-GRANOLA.md",
        ):
            self.assertFalse(is_ficha_filename(nome), nome)

    def test_operacionais_do_produto_ficam_fora(self):
        for nome in ("INDICE.md", "WORKFLOWS.md", "EMAIL-CURADORIA.md"):
            self.assertFalse(is_ficha_filename(nome), nome)

    def test_ocultos_rascunhos_e_legados_ficam_fora(self):
        for nome in (
            ".oculto_x_2026-01-01.md",
            "_rascunho.md",
            "ficha-3.md",
            "artigo-karpathy.md",
            "Autor_SemData.md",
        ):
            self.assertFalse(is_ficha_filename(nome), nome)


if __name__ == "__main__":
    unittest.main()
