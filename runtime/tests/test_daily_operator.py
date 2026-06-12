from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from prumo_runtime import __version__
from prumo_runtime.daily_operator import build_daily_actions, is_fresh_workspace


def _empty_overview() -> dict:
    return {"missing": {"generated": [], "derived": []}}


def _make_nested_workspace(
    workspace: Path,
    *,
    pauta_hot: str | None = None,
    inbox_item: str | None = None,
) -> None:
    (workspace / "Prumo" / "Agente").mkdir(parents=True, exist_ok=True)
    (workspace / "Prumo" / "Referencias").mkdir(parents=True, exist_ok=True)
    (workspace / ".prumo" / "state").mkdir(parents=True, exist_ok=True)
    (workspace / ".prumo" / "system").mkdir(parents=True, exist_ok=True)
    (workspace / "AGENT.md").write_text("# wrapper\n", encoding="utf-8")
    (workspace / "CLAUDE.md").write_text("# wrapper\n", encoding="utf-8")
    (workspace / "AGENTS.md").write_text("# wrapper\n", encoding="utf-8")
    (workspace / "Prumo" / "AGENT.md").write_text("# canonical\n", encoding="utf-8")
    hot_section = f"- {pauta_hot}\n" if pauta_hot else "_Nada ainda._\n"
    (workspace / "Prumo" / "PAUTA.md").write_text(
        "# Pauta\n\n## Quente (precisa de atenção agora)\n\n"
        f"{hot_section}\n## Em andamento\n\n_Nada ainda._\n\n## Agendado / Lembretes\n\n_Nada ainda._\n",
        encoding="utf-8",
    )
    inbox_section = f"- {inbox_item}\n" if inbox_item else "_Inbox limpo._\n"
    (workspace / "Prumo" / "INBOX.md").write_text(
        f"# Inbox\n\n{inbox_section}",
        encoding="utf-8",
    )
    (workspace / "Prumo" / "REGISTRO.md").write_text(
        "# Registro\n\n| Data | Origem | Resumo | Ação | Destino |\n|------|--------|--------|------|---------|\n",
        encoding="utf-8",
    )
    (workspace / "Prumo" / "IDEIAS.md").write_text(
        "# Ideias\n\n_Nenhuma ideia registrada ainda._\n", encoding="utf-8"
    )
    (workspace / "Prumo" / "Referencias" / "WORKFLOWS.md").write_text("# Workflows\n", encoding="utf-8")
    (workspace / ".prumo" / "system" / "PRUMO-CORE.md").write_text(
        f"> **prumo_version: {__version__}**\n",
        encoding="utf-8",
    )
    (workspace / ".prumo" / "state" / "workspace-schema.json").write_text(
        json.dumps(
            {
                "user_name": "Batata",
                "agent_name": "Prumo",
                "timezone": "America/Sao_Paulo",
                "briefing_time": "09:00",
                "layout_mode": "nested",
                "files": {"generated": [], "authorial": [], "derived": []},
            }
        ),
        encoding="utf-8",
    )
    (workspace / ".prumo" / "state" / "last-briefing.json").write_text('{"at": ""}', encoding="utf-8")


class IsFreshWorkspaceTests(unittest.TestCase):
    def test_empty_workspace_is_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            _make_nested_workspace(workspace)
            self.assertTrue(is_fresh_workspace(workspace))

    def test_workspace_with_hot_pauta_item_is_not_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            _make_nested_workspace(workspace, pauta_hot="Resolver IPTU atrasado")
            self.assertFalse(is_fresh_workspace(workspace))

    def test_workspace_with_inbox_item_is_not_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            _make_nested_workspace(workspace, inbox_item="Anotar ideia do podcast")
            self.assertFalse(is_fresh_workspace(workspace))


class BuildDailyActionsTests(unittest.TestCase):
    def _action_ids(self, actions: list[dict[str, object]]) -> list[str]:
        return [str(action["id"]) for action in actions]

    def test_fresh_workspace_offers_kickoff_first_before_briefing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            _make_nested_workspace(workspace)
            actions = build_daily_actions(workspace, _empty_overview(), has_briefed_today=False)
            ids = self._action_ids(actions)
            self.assertEqual(ids[0], "kickoff")
            self.assertTrue(actions[0]["recommended"])
            self.assertNotIn("briefing", ids)
            self.assertIn("kickoff_contract", actions[0])

    def test_fresh_workspace_offers_kickoff_first_even_after_briefing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            _make_nested_workspace(workspace)
            actions = build_daily_actions(workspace, _empty_overview(), has_briefed_today=True)
            ids = self._action_ids(actions)
            self.assertEqual(ids[0], "kickoff")
            self.assertTrue(actions[0]["recommended"])
            self.assertNotIn("briefing", ids)

    def test_seasoned_workspace_without_briefing_puts_briefing_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            _make_nested_workspace(workspace, pauta_hot="Resolver IPTU atrasado")
            actions = build_daily_actions(workspace, _empty_overview(), has_briefed_today=False)
            ids = self._action_ids(actions)
            self.assertEqual(ids[0], "briefing")
            self.assertNotIn("kickoff", ids)

    def test_seasoned_workspace_after_briefing_prefers_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            _make_nested_workspace(workspace, pauta_hot="Resolver IPTU atrasado")
            actions = build_daily_actions(workspace, _empty_overview(), has_briefed_today=True)
            ids = self._action_ids(actions)
            self.assertEqual(ids[0], "continue")
            self.assertNotIn("kickoff", ids)
            self.assertIn("briefing", ids)
            briefing = next(action for action in actions if action["id"] == "briefing")
            self.assertEqual(briefing["label"], "Rodar o briefing de novo")

    def test_repair_comes_first_when_structure_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            _make_nested_workspace(workspace)
            overview = {"missing": {"generated": ["PAUTA.md"], "derived": []}}
            actions = build_daily_actions(workspace, overview, has_briefed_today=False)
            ids = self._action_ids(actions)
            self.assertEqual(ids[0], "repair")
            self.assertIn("kickoff", ids)
            self.assertEqual(ids[1], "kickoff")


if __name__ == "__main__":
    unittest.main()
