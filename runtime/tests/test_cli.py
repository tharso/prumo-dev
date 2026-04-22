from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from prumo_runtime.cli import main


class CliDefaultInvocationTests(unittest.TestCase):
    def test_prumo_without_subcommand_behaves_like_start_in_workspace(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text("> **prumo_version: 4.15.1**\n", encoding="utf-8")
            (workspace / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
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
            os.chdir(workspace)
            try:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    rc = main([])
            finally:
                os.chdir(previous_cwd)
        self.assertEqual(rc, 0)
        rendered = buffer.getvalue()
        self.assertTrue(
            "o Prumo está de pé no workspace" in rendered
            or "acabou de nascer" in rendered
        )

    def test_prumo_without_subcommand_in_random_directory_explains_next_step(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    rc = main([])
            finally:
                os.chdir(previous_cwd)
        self.assertEqual(rc, 0)
        rendered = buffer.getvalue()
        self.assertIn("não parece workspace do Prumo", rendered)
        self.assertIn("prumo setup", rendered)

    def test_prumo_inbox_preview_subcommand_returns_preview_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            inbox_dir = workspace / "Inbox4Mobile"
            referencias = workspace / "Referencias"
            state_dir.mkdir(parents=True, exist_ok=True)
            inbox_dir.mkdir(parents=True, exist_ok=True)
            referencias.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text("> **prumo_version: 4.16.1**\n", encoding="utf-8")
            (workspace / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
            (workspace / "INBOX.md").write_text("# Inbox\n", encoding="utf-8")
            (workspace / "REGISTRO.md").write_text("# Registro\n", encoding="utf-8")
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
            (inbox_dir / "item.txt").write_text("https://example.com\n", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["inbox", "preview", "--workspace", str(workspace), "--format", "json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["preview"]["count"], 1)
        self.assertTrue(any(action["id"] == "process-inbox" for action in payload["actions"]))
