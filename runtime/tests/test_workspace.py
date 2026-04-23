from __future__ import annotations

import unittest

from prumo_runtime.workspace import extract_section


PAUTA_FIXTURE = """# Pauta

## Quente — Quarta 22/04

- Item quente 1
- Item quente 2

## Em andamento

- Item em andamento

## Agendado

- Item agendado normal

## Agendado Futuro

- Item agendado futuro distante

## Horizonte (importante mas não urgente)

- Item do horizonte
"""


class ExtractSectionTests(unittest.TestCase):
    """Match de seção tolera sufixo visual no header sem confundir seções parecidas."""

    def test_exact_header_match(self) -> None:
        text = "## Quente\n\n- Um item\n"
        self.assertEqual(extract_section(text, "Quente"), ["- Um item"])

    def test_header_with_em_dash_suffix_still_matches(self) -> None:
        # "## Quente — Quarta 22/04" deve bater pra heading="Quente"
        items = extract_section(PAUTA_FIXTURE, "Quente")
        self.assertEqual(items, ["- Item quente 1", "- Item quente 2"])

    def test_header_with_parenthesis_suffix_still_matches(self) -> None:
        # "## Horizonte (importante mas não urgente)" deve bater pra heading="Horizonte"
        items = extract_section(PAUTA_FIXTURE, "Horizonte")
        self.assertEqual(items, ["- Item do horizonte"])

    def test_header_with_slash_suffix_still_matches(self) -> None:
        # Compat com formato antigo "## Agendado / Lembretes"
        text = "## Agendado / Lembretes\n\n- Item legacy\n"
        self.assertEqual(extract_section(text, "Agendado"), ["- Item legacy"])

    def test_agendado_does_not_capture_agendado_futuro(self) -> None:
        # Sutileza crítica: "Agendado Futuro" é outra seção, NÃO pode ser engolida por "Agendado".
        items = extract_section(PAUTA_FIXTURE, "Agendado")
        self.assertEqual(items, ["- Item agendado normal"])

    def test_agendado_futuro_is_its_own_section(self) -> None:
        items = extract_section(PAUTA_FIXTURE, "Agendado Futuro")
        self.assertEqual(items, ["- Item agendado futuro distante"])

    def test_unknown_heading_returns_empty(self) -> None:
        self.assertEqual(extract_section(PAUTA_FIXTURE, "Não Existe"), [])

    def test_legacy_quente_precisa_de_atencao_still_works(self) -> None:
        # Quem ainda tem o formato antigo "## Quente (precisa de atenção agora)"
        # continua sendo atendido por heading="Quente".
        text = "## Quente (precisa de atenção agora)\n\n- Legacy item\n"
        self.assertEqual(extract_section(text, "Quente"), ["- Legacy item"])


if __name__ == "__main__":
    unittest.main()
