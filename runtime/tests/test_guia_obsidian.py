"""
Trava anti-drift do guia Obsidian (#149, épico #138).

O guia é bônus opcional — a restrição-mãe do épico é que o Obsidian nunca
vire requisito. Este teste trava as três pontas: o guia existe e declara a
não-obrigatoriedade; o dispatch tem o gatilho de intenção (senão a pergunta
"como uso com Obsidian?" cai em categoria genérica — achado do Codex no
design); o README aponta o guia.
"""
from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GUIA = REPO_ROOT / "skills" / "prumo" / "references" / "guia-obsidian.md"
DISPATCH = (
    REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "dispatch.md"
)
README = REPO_ROOT / "README.md"


class GuiaObsidianTests(unittest.TestCase):
    def test_guia_existe_e_declara_nao_obrigatoriedade(self) -> None:
        """O guia existe, cobre os bônus e deixa claro que nada é requisito."""
        self.assertTrue(GUIA.exists(), f"faltando: {GUIA}")
        text = GUIA.read_text(encoding="utf-8")
        lower = text.lower()
        # A restrição-mãe, em todas as letras.
        self.assertIn("nunca", lower)
        self.assertIn("requisito", lower)
        # Os bônus prometidos pelas etapas anteriores.
        self.assertIn("grafo", lower)
        self.assertIn("backlinks", lower)
        self.assertIn("[[", text, "o guia deve explicar os wikilinks das fichas")
        # Calendário é extensão de terceiro, não recurso nativo.
        self.assertIn("extensão", lower)
        # Fronteira: o Prumo não escreve no vault pessoal do usuário.
        self.assertIn("vault", lower)

    def test_dispatch_tem_o_gatilho(self) -> None:
        """A tabela de intenções roteia perguntas sobre Obsidian pro guia."""
        text = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("Obsidian", text)
        self.assertIn("guia-obsidian.md", text)

    def test_readme_aponta_o_guia(self) -> None:
        """O README tem a seção opcional apontando o guia."""
        text = README.read_text(encoding="utf-8")
        self.assertIn("Obsidian", text)


if __name__ == "__main__":
    unittest.main()
