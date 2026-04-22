from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

from prumo_runtime import __version__
from prumo_runtime.commands.inbox_preview import build_inbox_preview_payload, run_inbox_preview


class InboxPreviewCommandTests(unittest.TestCase):
    def _build_workspace(self, root: Path) -> Path:
        workspace = root
        state_dir = workspace / "_state"
        inbox_dir = workspace / "Inbox4Mobile"
        referencias = workspace / "Referencias"
        state_dir.mkdir(parents=True, exist_ok=True)
        inbox_dir.mkdir(parents=True, exist_ok=True)
        referencias.mkdir(parents=True, exist_ok=True)
        (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
        (workspace / "PAUTA.md").write_text("# Pauta\n\n- Item quente\n", encoding="utf-8")
        (workspace / "INBOX.md").write_text("# Inbox\n\n- triar item 1\n", encoding="utf-8")
        (workspace / "REGISTRO.md").write_text("# Registro\n", encoding="utf-8")
        (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
        (workspace / "Referencias" / "WORKFLOWS.md").write_text("# Workflows\n", encoding="utf-8")
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
        (state_dir / "last-briefing.json").write_text('{"at": ""}', encoding="utf-8")
        (inbox_dir / "_processed.json").write_text('{"version":"1.0","items":[]}\n', encoding="utf-8")
        (inbox_dir / "2026-03-23_text.txt").write_text(
            "https://youtu.be/QT7W_uHjqWE\nCriar nota sobre o video.\n",
            encoding="utf-8",
        )
        return workspace

    def test_build_inbox_preview_payload_exposes_preview_and_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._build_workspace(Path(tmpdir))
            payload = build_inbox_preview_payload(workspace)
            self.assertEqual(payload["workspace_path"], str(workspace.resolve()))
            self.assertEqual(payload["preview"]["count"], 1)
            self.assertTrue(payload["preview"]["preview_path"].endswith("inbox-preview.html"))
            self.assertTrue(any(action["id"] == "process-inbox" for action in payload["actions"]))
            self.assertTrue(any(action["id"] == "workflow-scaffold" for action in payload["actions"]))
            self.assertIn("preview", payload)
            self.assertIn("sample", payload["preview"])

    def test_run_inbox_preview_json_output_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._build_workspace(Path(tmpdir))
            args = Namespace(workspace=str(workspace), format="json")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_inbox_preview(args)
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["preview"]["count"], 1)
            self.assertEqual(payload["preview"]["items"][0]["filename"], "2026-03-23_text.txt")
            self.assertTrue(payload["preview"]["sample"])

    def test_run_inbox_preview_text_output_mentions_vitrine(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._build_workspace(Path(tmpdir))
            args = Namespace(workspace=str(workspace), format="text")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_inbox_preview(args)
            self.assertEqual(rc, 0)
            rendered = buffer.getvalue()
            self.assertIn("Inbox preview do workspace", rendered)
            self.assertIn("Itens pendentes para triagem", rendered)
            self.assertIn("vitrine", rendered)
