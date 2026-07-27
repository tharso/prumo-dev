"""#180 PR12 (opção B do dono, 16/07): a voz da higiene vem do PERFIL.

As 6 linhas `**Tom:**` roteirizadas viraram `**Intenção:**` (o que
comunicar) + exemplo ROTULADO como ilustração — fala decorada em skill é
telemarketing, não parceria. O grep-guard trava o rótulo e proíbe a volta
do script.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HIGIENE = REPO_ROOT / "skills" / "higiene" / "SKILL.md"

EXAMPLE_LABEL = "Exemplo (voz Equilibrada — não é script):"


class HigieneVozTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = HIGIENE.read_text(encoding="utf-8")

    def test_no_scripted_tom_lines(self) -> None:
        self.assertNotIn(
            "**Tom:**",
            self.text,
            "linha de fala roteirizada voltou — a voz vem do PERFIL (#180 PR12)",
        )

    def test_six_intencao_lines_with_labeled_examples(self) -> None:
        self.assertEqual(self.text.count("**Intenção:**"), 6)
        self.assertEqual(self.text.count(EXAMPLE_LABEL), 6)

    def test_voice_section_points_to_perfil(self) -> None:
        self.assertIn("## Voz das propostas", self.text)
        self.assertIn("Prumo/Agente/PERFIL.md", self.text)
        self.assertIn("nunca script pra repetir", self.text)

    def test_every_example_follows_an_intencao(self) -> None:
        # O rótulo nunca aparece órfão: cada exemplo ilustra uma Intenção
        # declarada logo acima (mesma detecção).
        blocks = self.text.split("**Intenção:**")[1:]
        self.assertEqual(len(blocks), 6)
        for i, block in enumerate(blocks, start=1):
            with self.subTest(deteccao=i):
                self.assertIn(EXAMPLE_LABEL, block.split("###")[0])


if __name__ == "__main__":
    unittest.main()
