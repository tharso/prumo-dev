from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from prumo_runtime.cli import main


class SetupCommandTests(unittest.TestCase):
    def test_setup_creates_nested_workspace_layout_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "PrumoPilot"
            buffer = io.StringIO()
            with patch(
                "builtins.input",
                side_effect=[
                    "Batata",
                    str(workspace),
                    "a",
                ],
            ):
                with redirect_stdout(buffer):
                    rc = main(["setup"])
            self.assertEqual(rc, 0)
            self.assertTrue((workspace / "AGENT.md").exists())
            self.assertTrue((workspace / "AGENTS.md").exists())
            self.assertTrue((workspace / "CLAUDE.md").exists())
            self.assertTrue((workspace / "Prumo" / "AGENT.md").exists())
            self.assertTrue((workspace / "Prumo" / "PAUTA.md").exists())
            self.assertTrue((workspace / ".prumo" / "state" / "workspace-schema.json").exists())
            self.assertTrue((workspace / ".prumo" / "system" / "PRUMO-CORE.md").exists())
            self.assertFalse((workspace / "PAUTA.md").exists())

            rendered = buffer.getvalue()
            self.assertIn("Etapa 1 de 3", rendered)
            self.assertIn("Etapa 2 de 3", rendered)
            self.assertIn("Etapa 3 de 3", rendered)
            self.assertIn("Entre no workspace e rode `prumo`", rendered)

    def test_setup_adopt_mode_can_merge_existing_root_wrappers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "DailyLife"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# Meu AGENT\n\nNotas minhas.\n", encoding="utf-8")
            (workspace / "CLAUDE.md").write_text("# Meu CLAUDE\n", encoding="utf-8")
            buffer = io.StringIO()
            with patch(
                "builtins.input",
                side_effect=[
                    "Batata",
                    str(workspace),
                    "a",
                    "a",
                ],
            ):
                with redirect_stdout(buffer):
                    rc = main(["setup"])
            self.assertEqual(rc, 0)
            merged_agent = (workspace / "AGENT.md").read_text(encoding="utf-8")
            self.assertIn("Notas minhas.", merged_agent)
            self.assertIn("<!-- prumo:begin -->", merged_agent)
            self.assertIn("Prumo detectado neste workspace.", merged_agent)
            self.assertTrue((workspace / ".prumo" / "backups" / "setup").exists())
            self.assertTrue((workspace / "Prumo" / "AGENT.md").exists())
            rendered = buffer.getvalue()
            self.assertIn("Wrappers mesclados", rendered)
