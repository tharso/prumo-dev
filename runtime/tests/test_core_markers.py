"""Marcadores estruturais do core (#178, épico #177).

O staging fásico da rota do briefing (M3) lê o core POR MARCADOR — "até
`# Parte 2`" na abertura, `## Guardrails` sob demanda — em vez de fatiar o
arquivo (18+ refs hardcoded, #134). Estes guards garantem que os marcadores
existem e mantêm a ordem esperada; renomear qualquer um deles quebra o CI
antes de quebrar a rota.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md"

PARTE_1 = "# Parte 1 — Identidade e interação"
PARTE_2 = "# Parte 2 — Playbooks operacionais"
GUARDRAILS = "## Guardrails"


class CoreMarkersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CORE.read_text(encoding="utf-8")
        cls.lines = [line.strip() for line in cls.text.splitlines()]

    def test_parte1_parte2_guardrails_headers_exist(self) -> None:
        for marker in (PARTE_1, PARTE_2, GUARDRAILS):
            self.assertIn(
                marker,
                self.lines,
                f"marcador estrutural sumiu do core: {marker!r} — o staging da rota depende dele",
            )

    def test_guardrails_dentro_da_parte2(self) -> None:
        idx_p1 = self.lines.index(PARTE_1)
        idx_p2 = self.lines.index(PARTE_2)
        idx_guard = self.lines.index(GUARDRAILS)
        self.assertLess(idx_p1, idx_p2, "Parte 1 deve vir antes da Parte 2")
        self.assertLess(
            idx_p2,
            idx_guard,
            "## Guardrails deve morar na Parte 2 (é carregado sob demanda pelo playbook)",
        )

    def test_comandos_disponiveis_na_parte1(self) -> None:
        # A tabela canônica de comandos (fonte do /menu e, na M2, da cadeia
        # de fallback) mora na Parte 1 — sempre carregada.
        idx_cmd = self.lines.index("## Comandos disponíveis")
        idx_p2 = self.lines.index(PARTE_2)
        self.assertLess(idx_cmd, idx_p2)


if __name__ == "__main__":
    unittest.main()
