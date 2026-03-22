from __future__ import annotations

import unittest

from prumo_runtime import templates


class TemplateAdapterTests(unittest.TestCase):
    def test_agents_wrapper_includes_short_invocation_contract(self) -> None:
        rendered = templates.render_agents_wrapper("Batata", "Prumo")
        self.assertIn('Se o usuário disser "Prumo"', rendered)
        self.assertIn("rode `prumo`", rendered)
        self.assertIn("prumo briefing --workspace . --refresh-snapshot", rendered)
        self.assertIn("prumo start --format json", rendered)
        self.assertIn("prumo briefing --workspace . --refresh-snapshot --format json", rendered)
        self.assertIn("adapter_hints", rendered)
        self.assertIn("Não leia arquivo para simular", rendered)
        self.assertIn("Não escreva `_state/`", rendered)
        self.assertIn("Não rode comando extra sem necessidade", rendered)

    def test_agent_md_mentions_host_invocation_rules(self) -> None:
        rendered = templates.render_agent_md(
            user_name="Batata",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
        )
        self.assertIn('Se o usuário chamar "Prumo"', rendered)
        self.assertIn("host deve rodar `prumo`", rendered)
        self.assertIn("prumo briefing --workspace . --refresh-snapshot", rendered)
        self.assertIn("prumo briefing --workspace . --refresh-snapshot --format json", rendered)
        self.assertIn("adapter_hints", rendered)
        self.assertIn("Não leia arquivo para simular", rendered)
        self.assertIn("Não escreva arquivos em `_state/`", rendered)
        self.assertIn("Não rode comando extra só porque ficou curioso", rendered)
