from __future__ import annotations

import unittest

from prumo_runtime import templates


class TemplateAdapterTests(unittest.TestCase):
    def test_agents_wrapper_includes_short_invocation_contract(self) -> None:
        rendered = templates.render_agents_wrapper("Batata", "Prumo")
        self.assertIn('Se o usuário disser "Prumo"', rendered)
        self.assertIn("`prumo:abrir`", rendered)
        self.assertIn("atalho equivalente", rendered)
        self.assertIn("prumo briefing --workspace .", rendered)
        self.assertIn("prumo start --format json", rendered)
        self.assertIn("prumo briefing --workspace . --format json", rendered)
        self.assertIn("adapter_hints", rendered)
        self.assertIn("state_flags", rendered)
        self.assertIn("degradation", rendered)
        self.assertIn("selection_contract", rendered)
        self.assertIn("Não leia arquivo para simular", rendered)
        self.assertIn("Não escreva `_state/`", rendered)
        self.assertIn("Não rode comando extra sem necessidade", rendered)
        self.assertIn("next_move.id == kickoff", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)

    def test_nested_wrapper_points_to_real_core_and_state_paths(self) -> None:
        rendered = templates.render_claude_wrapper(
            "Batata",
            "Prumo",
            canonical_target="Prumo/AGENT.md",
            context_root="Prumo/Agente/",
            core_path=".prumo/system/PRUMO-CORE.md",
            state_path=".prumo/state/",
        )
        self.assertIn("Leia `Prumo/AGENT.md`", rendered)
        self.assertIn("Use `.prumo/system/PRUMO-CORE.md`", rendered)
        self.assertIn("Não escreva `.prumo/state/`", rendered)
        self.assertIn("next_move.id == kickoff", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)

    def test_agent_md_mentions_host_invocation_rules(self) -> None:
        rendered = templates.render_agent_md(
            user_name="Batata",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
        )
        self.assertIn('Se o usuário chamar "Prumo"', rendered)
        self.assertIn("`prumo:abrir`", rendered)
        self.assertIn("atalho equivalente", rendered)
        self.assertIn("prumo briefing --workspace .", rendered)
        self.assertIn("prumo briefing --workspace . --format json", rendered)
        self.assertIn("adapter_hints", rendered)
        self.assertIn("state_flags", rendered)
        self.assertIn("degradation", rendered)
        self.assertIn("selection_contract", rendered)
        self.assertIn("Não leia arquivo para simular", rendered)
        self.assertIn("Não escreva arquivos em `_state/`", rendered)
        self.assertIn("Não rode comando extra só porque ficou curioso", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)

    def test_workflows_template_exposes_structure_only_phase(self) -> None:
        rendered = templates.render_workflows_md("22/03/2026")
        self.assertIn("structure-only", rendered)
        self.assertIn("candidatos", rendered.lower())
        self.assertIn("22/03/2026", rendered)

    def test_agente_index_can_point_to_nested_core_path(self) -> None:
        rendered = templates.render_agente_index(
            "Batata",
            "America/Sao_Paulo",
            "09:00",
            "30/03/2026",
            core_path=".prumo/system/PRUMO-CORE.md",
        )
        self.assertIn("`.prumo/system/PRUMO-CORE.md`", rendered)
