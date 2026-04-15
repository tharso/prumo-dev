from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
import io
import os
from pathlib import Path

from prumo_runtime.commands.briefing import (
    build_briefing_payload,
    choose_proposal,
    run_briefing,
)
from prumo_runtime import __version__
from prumo_runtime.platform_support import platform_label


class BriefingTests(unittest.TestCase):
    def test_build_briefing_payload_exposes_sections_and_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            inbox_dir = workspace / "Inbox4Mobile"
            state_dir.mkdir(parents=True, exist_ok=True)
            inbox_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "PAUTA.md").write_text(
                "# Pauta\n\n## Quente (precisa de atenção agora)\n\n- Ajuste urgente no site\n\n"
                "## Em andamento\n\n- Projeto X\n\n## Agendado / Lembretes\n\n- Revisão semanal\n",
                encoding="utf-8",
            )
            (workspace / "INBOX.md").write_text("# Inbox\n\n_Inbox limpo._\n", encoding="utf-8")
            (state_dir / "workspace-schema.json").write_text(
                json.dumps(
                    {
                        "user_name": "Batata",
                        "agent_name": "Prumo",
                        "timezone": "America/Sao_Paulo",
                        "briefing_time": "09:00",
                        "files": {"generated": [], "authorial": [], "derived": []},
                    }
                ),
                encoding="utf-8",
            )
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
            (state_dir / "briefing-state.json").write_text('{"last_briefing_at": ""}', encoding="utf-8")
            payload = build_briefing_payload(workspace, refresh_snapshot=False)
            self.assertEqual(payload["workspace_path"], str(workspace.resolve()))
            self.assertEqual(payload["adapter_contract_version"], "2026-03-28")
            self.assertTrue(payload["sections"])
            self.assertEqual(payload["sections"][0]["id"], "preflight")
            self.assertTrue(payload["canonical_refs"]["briefing_procedure"].endswith("modules/briefing-procedure.md"))
            self.assertEqual(payload["proposal"]["options"][0]["id"], "continue")
            self.assertIn("Proposta do dia", payload["message"])
            self.assertIn("actions", payload)
            self.assertFalse(any(action["id"] == "workflow-scaffold" for action in payload["actions"]))
            self.assertEqual(payload["daily_operation"]["mode"], "daily-operator")
            self.assertTrue(payload["capabilities"]["daily_operation"]["documentation"])
            self.assertIn("documentation_contract", payload["daily_operation"])
            self.assertEqual(payload["next_move"]["id"], "continue")

    def test_run_briefing_json_output_uses_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            inbox_dir = workspace / "Inbox4Mobile"
            state_dir.mkdir(parents=True, exist_ok=True)
            inbox_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "PAUTA.md").write_text(
                "# Pauta\n\n## Quente (precisa de atenção agora)\n\n- Ajuste urgente no site\n",
                encoding="utf-8",
            )
            (workspace / "INBOX.md").write_text("# Inbox\n\n_Inbox limpo._\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
            (state_dir / "workspace-schema.json").write_text(
                json.dumps(
                    {
                        "user_name": "Batata",
                        "agent_name": "Prumo",
                        "timezone": "America/Sao_Paulo",
                        "briefing_time": "09:00",
                        "files": {"generated": [], "authorial": [], "derived": []},
                    }
                ),
                encoding="utf-8",
            )
            (state_dir / "briefing-state.json").write_text('{"last_briefing_at": ""}', encoding="utf-8")
            args = Namespace(workspace=str(workspace), refresh_snapshot=False, format="json")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_briefing(args)
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["workspace_path"], str(workspace.resolve()))
            self.assertEqual(payload["adapter_contract_version"], "2026-03-28")
            self.assertIn("sections", payload)
            self.assertEqual(payload["sections"][0]["label"], "Preflight")
            self.assertTrue(payload["canonical_refs"]["inbox_processing"].endswith("modules/inbox-processing.md"))
            self.assertIn("proposal", payload)
            self.assertIn("actions", payload)
            self.assertIn("next_move", payload)
            self.assertIn("selection_contract", payload)
            self.assertIn("degradation", payload)
            self.assertEqual(payload["platform"]["label"], platform_label())
            self.assertFalse(any(section["id"] == "workflow_scaffolding" for section in payload["sections"]))
            self.assertFalse(any(section["id"] == "apple_reminders" for section in payload["sections"]))
            self.assertTrue(any("documentation_targets" in action for action in payload["actions"]))
            self.assertEqual(payload["selection_contract"]["accepts_next_move"], "continue")
            self.assertIn("aceitar", payload["selection_contract"]["accept_tokens"])

    def test_choose_proposal_prefers_quente_over_andamento(self) -> None:
        proposal = choose_proposal(
            ["Ajuste urgente"],
            ["Agendado X"],
            ["Decidir abertura de empresa"],
        )
        self.assertEqual(proposal, "Ajuste urgente")

    def test_choose_proposal_falls_back_to_andamento(self) -> None:
        proposal = choose_proposal(
            [],
            [],
            ["Decidir abertura de empresa"],
        )
        self.assertEqual(proposal, "Decidir abertura de empresa")

    def test_choose_proposal_returns_fallback_when_empty(self) -> None:
        proposal = choose_proposal([], [], [])
        self.assertIn("dump real de pendências", proposal)


if __name__ == "__main__":
    unittest.main()
