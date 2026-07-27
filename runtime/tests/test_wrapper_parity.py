"""Paridade dos wrappers da raiz e fonte única das regras (#179, épico #177).

Critério 2 do épico: os 3 adapters da raiz (CLAUDE/AGENT/AGENTS.md) nascem
de um builder único e o bloco gerenciado de regras ("Porta curta") é
byte-igual entre eles — só o blurb e a instrução primária variam por
superfície. As regras vêm de UMA lista (`wrapper_rules.RULES`), com marcação
por superfície; regra com duas casas quebra aqui.
"""

from __future__ import annotations

import unittest

from prumo_runtime import templates
from prumo_runtime.wrapper_rules import RULES, render_rules, rules_for

STATE = ".prumo/state/"
COMMON = dict(
    canonical_target="Prumo/AGENT.md",
    context_root="Prumo/Agente/",
    core_path=".prumo/system/PRUMO-CORE.md",
    state_path=STATE,
)


def _porta_curta(rendered: str) -> str:
    start = rendered.index("## Porta curta")
    end = rendered.index("## Instrução primária")
    return rendered[start:end].strip()


class WrapperParityTest(unittest.TestCase):
    def _render_three(self) -> list[str]:
        # Paridade da fonte única é medida no MESMO perfil (full): os
        # defaults por superfície divergem desde a #180 (CLAUDE.md minimal —
        # host com registry; AGENT/AGENTS full — hosts crus).
        claude = templates.render_claude_wrapper("Teste", "Prumo", profile="full", **COMMON)
        agents = templates.render_agents_wrapper("Teste", "Prumo", **COMMON)
        agent = templates.render_agent_root_wrapper(
            "Teste", "Prumo", canonical_target="Prumo/AGENT.md", system_root=STATE
        )
        return [claude, agent, agents]

    def test_three_root_wrappers_share_identical_managed_rules(self) -> None:
        blocks = [_porta_curta(rendered) for rendered in self._render_three()]
        self.assertEqual(
            blocks[0],
            blocks[1],
            "Porta curta divergiu entre CLAUDE.md e AGENT.md — fonte única quebrada",
        )
        self.assertEqual(blocks[0], blocks[2])

    def test_claude_default_is_minimal_subset_from_same_source(self) -> None:
        # #180: o default do CLAUDE.md é minimal — e as regras minimal vêm da
        # MESMA fonte única (render_rules com profile), nunca de texto avulso.
        claude_default = templates.render_claude_wrapper("Teste", "Prumo", **COMMON)
        self.assertIn(render_rules("wrapper", state_path=STATE, profile="minimal"), claude_default)
        minimal_rules = set(rules_for("wrapper", profile="minimal"))
        full_rules = set(rules_for("wrapper", profile="full"))
        self.assertTrue(minimal_rules <= full_rules, "minimal tem regra fora do full")
        self.assertLess(len(minimal_rules), len(full_rules))

    def test_wrappers_derive_from_single_source(self) -> None:
        expected = render_rules("wrapper", state_path=STATE)
        for rendered in self._render_three():
            self.assertIn(expected, rendered)

    def test_workspace_rules_derive_from_single_source(self) -> None:
        rendered = templates.render_agent_md(
            user_name="Teste",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
            state_path=STATE,
        )
        self.assertIn(render_rules("workspace", state_path=STATE), rendered)

    def test_flavor_blurbs_still_distinguish_surfaces(self) -> None:
        claude, agent, agents = self._render_three()
        self.assertIn("Compatibilidade para Claude/Cowork", claude)
        self.assertIn("hosts que procuram `AGENT.md` na raiz", agent)
        self.assertIn("ambientes que procuram `AGENTS.md`", agents)


class RuleSourceTest(unittest.TestCase):
    def test_rule_ids_and_texts_are_unique(self) -> None:
        ids = [rule.id for rule in RULES]
        texts = [rule.text for rule in RULES]
        self.assertEqual(len(ids), len(set(ids)), "id de regra duplicado")
        self.assertEqual(len(texts), len(set(texts)), "regra com duas casas (texto duplicado)")

    def test_surface_counts_match_contract(self) -> None:
        # #228 C1: 9 regras de consumo de JSON viraram runtime-consumo.md
        # (dono único, carregado no uso); as superfícies ganharam o ponteiro.
        self.assertEqual(len(rules_for("wrapper")), 12)
        self.assertEqual(len(rules_for("workspace")), 14)

    def test_minimal_profile_accepted_and_subset_of_full(self) -> None:
        minimal = set(rules_for("wrapper", profile="minimal"))
        full = set(rules_for("wrapper"))
        self.assertTrue(minimal)
        self.assertLess(len(minimal), len(full))
        self.assertTrue(minimal <= full, "perfil minimal tem regra fora do full")

    def test_invalid_surface_or_profile_raises(self) -> None:
        with self.assertRaises(ValueError):
            rules_for("desktop")
        with self.assertRaises(ValueError):
            rules_for("wrapper", profile="turbo")

    def test_numbering_is_sequential_per_surface(self) -> None:
        rendered = render_rules("workspace", state_path=STATE)
        numbers = [
            int(line.split(".", 1)[0])
            for line in rendered.splitlines()
            if line and line[0].isdigit()
        ]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))


if __name__ == "__main__":
    unittest.main()
