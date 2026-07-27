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
        # Âncoras DENTRO da seção (round 2 do Codex): menção solta em outro
        # lugar não conta como contrato da voz.
        self.assertIn("## Voz das propostas", self.text)
        section = self.text.split("## Voz das propostas", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Prumo/Agente/PERFIL.md", section)
        self.assertIn("nunca script pra repetir", section)
        self.assertIn("Direto, Equilibrado, Gentil ou o dele próprio", section)

    def test_every_example_follows_an_intencao(self) -> None:
        # O exemplo vem IMEDIATAMENTE após a Intenção (próxima linha não
        # vazia) — em qualquer outro lugar, o rótulo vira decoração solta
        # (review Codex do PR12).
        blocks = self.text.split("**Intenção:**")[1:]
        self.assertEqual(len(blocks), 6)
        for i, block in enumerate(blocks, start=1):
            with self.subTest(deteccao=i):
                lines = block.splitlines()
                # linha 0 = resto da linha da Intenção; a próxima não-vazia
                # tem que ser o exemplo rotulado.
                next_line = next((l for l in lines[1:] if l.strip()), "")
                self.assertTrue(
                    next_line.startswith(EXAMPLE_LABEL),
                    f"detecção {i}: exemplo não segue imediatamente a Intenção ({next_line[:60]!r})",
                )


if __name__ == "__main__":
    unittest.main()
