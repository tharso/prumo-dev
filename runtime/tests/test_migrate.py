from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from prumo_runtime.cli import main


class MigrateCommandTests(unittest.TestCase):
    def test_migrate_moves_flat_workspace_to_nested_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "DailyLife"
            (workspace / "Agente").mkdir(parents=True, exist_ok=True)
            (workspace / "Referencias").mkdir(parents=True, exist_ok=True)
            (workspace / "Inbox4Mobile").mkdir(parents=True, exist_ok=True)
            (workspace / "_state").mkdir(parents=True, exist_ok=True)
            (workspace / "_logs").mkdir(parents=True, exist_ok=True)

            (workspace / "AGENT.md").write_text("# AGENT legado\n", encoding="utf-8")
            (workspace / "CLAUDE.md").write_text("# Meu CLAUDE\n\nNotas do usuario.\n", encoding="utf-8")
            (workspace / "AGENTS.md").write_text("# AGENTS legado\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text("> **prumo_version: 4.17.0**\n", encoding="utf-8")
            (workspace / "PAUTA.md").write_text("# Pauta\n\n- Tarefa antiga\n", encoding="utf-8")
            (workspace / "INBOX.md").write_text("# Inbox\n\n- Entrada antiga\n", encoding="utf-8")
            (workspace / "REGISTRO.md").write_text("# Registro\n\n- Ontem\n", encoding="utf-8")
            (workspace / "IDEIAS.md").write_text("# Ideias\n\n- Uma ideia\n", encoding="utf-8")
            (workspace / "Agente" / "INDEX.md").write_text("# Índice antigo\n", encoding="utf-8")
            (workspace / "Referencias" / "WORKFLOWS.md").write_text("# Workflows antigos\n", encoding="utf-8")
            (workspace / "Inbox4Mobile" / "_processed.json").write_text("[]\n", encoding="utf-8")
            (workspace / "_state" / "workspace-schema.json").write_text(
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
            (workspace / "_state" / "briefing-state.json").write_text(
                '{"last_briefing_at": ""}',
                encoding="utf-8",
            )
            (workspace / "_state" / "google-integration.json").write_text(
                '{"status":"disconnected"}',
                encoding="utf-8",
            )
            (workspace / "_logs" / "runtime.log").write_text("linha\n", encoding="utf-8")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["migrate", "--workspace", str(workspace)])

            self.assertEqual(rc, 0)
            self.assertTrue((workspace / "AGENT.md").exists())
            self.assertTrue((workspace / "CLAUDE.md").exists())
            self.assertTrue((workspace / "AGENTS.md").exists())
            self.assertTrue((workspace / "Prumo" / "AGENT.md").exists())
            self.assertTrue((workspace / "Prumo" / "PAUTA.md").exists())
            self.assertTrue((workspace / "Prumo" / "INBOX.md").exists())
            self.assertTrue((workspace / "Prumo" / "REGISTRO.md").exists())
            self.assertTrue((workspace / "Prumo" / "IDEIAS.md").exists())
            self.assertTrue((workspace / "Prumo" / "Agente" / "INDEX.md").exists())
            self.assertTrue((workspace / "Prumo" / "Agente" / "LEGADO-CLAUDE.md").exists())
            self.assertTrue((workspace / ".prumo" / "state" / "workspace-schema.json").exists())
            self.assertTrue((workspace / ".prumo" / "state" / "last-briefing.json").exists())
            self.assertFalse((workspace / ".prumo" / "state" / "briefing-state.json").exists())
            self.assertTrue((workspace / ".prumo" / "logs" / "runtime.log").exists())
            self.assertTrue((workspace / ".prumo" / "system" / "PRUMO-CORE.md").exists())

            self.assertFalse((workspace / "PAUTA.md").exists())
            self.assertFalse((workspace / "INBOX.md").exists())
            self.assertFalse((workspace / "REGISTRO.md").exists())
            self.assertFalse((workspace / "IDEIAS.md").exists())
            self.assertFalse((workspace / "PRUMO-CORE.md").exists())
            self.assertFalse((workspace / "_state").exists())
            self.assertFalse((workspace / "_logs").exists())

            self.assertIn("Tarefa antiga", (workspace / "Prumo" / "PAUTA.md").read_text(encoding="utf-8"))
            self.assertIn(
                "Notas do usuario.",
                (workspace / "Prumo" / "Agente" / "LEGADO-CLAUDE.md").read_text(encoding="utf-8"),
            )

            schema = json.loads((workspace / ".prumo" / "state" / "workspace-schema.json").read_text(encoding="utf-8"))
            self.assertEqual(schema["layout_mode"], "nested")

            rendered = buffer.getvalue()
            self.assertIn("migrado para o layout novo", rendered)
            self.assertIn("Arquivos e diretórios movidos", rendered)

