"""#180 PR12 (opção B do dono, 16/07): a voz da higiene vem do PERFIL.

As 6 linhas `**Tom:**` roteirizadas viraram `**Intenção:**` (o que
comunicar) + exemplo ROTULADO como ilustração — fala decorada em skill é
telemarketing, não parceria. O grep-guard trava o rótulo e proíbe a volta
do script.
"""
from __future__ import annotations

import re

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

    def _secoes(self) -> dict[str, str]:
        partes = re.split(r"^### (\d+\. [^\n]+)$", self.text, flags=re.M)[1:]
        return dict(zip(partes[::2], partes[1::2]))

    def test_toda_deteccao_que_propoe_tem_intencao_e_exemplo(self) -> None:
        """Cobertura por SEÇÃO, não número mágico. Fixar `6` fazia o guard
        precisar de manutenção a cada check novo, e número desatualizado
        reprova o certo — a pior forma de guard. O contrato real é: quem faz
        proposta em voz declara a Intenção e rotula o exemplo."""
        faltando = [
            titulo for titulo, corpo in self._secoes().items()
            if "**Propor" in corpo
            and not ("**Intenção:**" in corpo and EXAMPLE_LABEL in corpo)
        ]
        self.assertEqual(faltando, [], f"detecção propõe sem Intenção rotulada: {faltando}")

    def test_intencao_nao_aparece_fora_de_deteccao(self) -> None:
        """Negativa: rótulo solto fora de seção de detecção é decoração."""
        dentro = sum(c.count("**Intenção:**") for c in self._secoes().values())
        self.assertEqual(dentro, self.text.count("**Intenção:**"))

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
        self.assertTrue(blocks, "nenhuma Intenção no documento")
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
