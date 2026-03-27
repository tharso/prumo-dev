from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime import __version__
from prumo_runtime.commands.start import run_start
from prumo_runtime.platform_support import platform_label


class StartCommandTests(unittest.TestCase):
    def test_missing_workspace_suggests_setup(self) -> None:
        missing = Path("/tmp/prumo-workspace-que-nao-existe")
        args = Namespace(workspace=str(missing), format="text")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = run_start(args)
        self.assertEqual(rc, 0)
        rendered = buffer.getvalue()
        self.assertIn("Não achei o workspace", rendered)
        self.assertIn("prumo setup", rendered)

    def test_legacy_workspace_suggests_migrate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "CLAUDE.md").write_text("# legado\n", encoding="utf-8")
            args = Namespace(workspace=str(workspace), format="text")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_start(args)
            self.assertEqual(rc, 0)
            rendered = buffer.getvalue()
            self.assertIn("migrate", rendered)
            self.assertIn("workspace legado", rendered)

    def test_start_without_workspace_uses_current_directory(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "CLAUDE.md").write_text("# wrapper\n", encoding="utf-8")
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
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            os.chdir(workspace)
            try:
                args = Namespace(workspace=None, format="text")
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    rc = run_start(args)
            finally:
                os.chdir(previous_cwd)
            self.assertEqual(rc, 0)
            rendered = buffer.getvalue()
            self.assertIn("o Prumo está de pé no workspace", rendered)
            self.assertIn(str(workspace), rendered)

    def test_workspace_discovery_stops_before_far_parent_match(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            deep = root
            for index in range(10):
                deep = deep / f"nivel-{index}"
            deep.mkdir(parents=True, exist_ok=True)
            (root / "CLAUDE.md").write_text("# legado longe demais\n", encoding="utf-8")
            os.chdir(deep)
            try:
                args = Namespace(workspace=None, format="text")
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    rc = run_start(args)
            finally:
                os.chdir(previous_cwd)
            self.assertEqual(rc, 0)
            rendered = buffer.getvalue()
            self.assertIn("não parece workspace do Prumo", rendered)

    def test_start_without_workspace_in_random_directory_suggests_setup_or_explicit_path(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            random_dir = Path(tmpdir)
            os.chdir(random_dir)
            try:
                args = Namespace(workspace=None, format="text")
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    rc = run_start(args)
            finally:
                os.chdir(previous_cwd)
            self.assertEqual(rc, 0)
            rendered = buffer.getvalue()
            self.assertIn("não parece workspace do Prumo", rendered)
            self.assertIn("prumo setup", rendered)
            self.assertIn("prumo start --workspace /caminho/do/workspace", rendered)

    def test_healthy_workspace_recommends_briefing_before_first_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "PAUTA.md").write_text(
                "# Pauta\n\n## Quente (precisa de atenção agora)\n\n- Ajuste urgente no site\n",
                encoding="utf-8",
            )
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text("> **prumo_version: 4.13.2**\n", encoding="utf-8")
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
            (state_dir / "google-integration.json").write_text(
                '{"status":"connected","active_profile":"pessoal","profiles":{"pessoal":{"status":"connected","account_email":"tharso@gmail.com"}}}',
                encoding="utf-8",
            )
            (state_dir / "apple-reminders-integration.json").write_text(
                '{"status":"connected","authorization_status":"fullAccess","lists":["A vida..."],"observed_lists":["A vida..."]}',
                encoding="utf-8",
            )
            args = Namespace(workspace=str(workspace), format="text")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_start(args)
            self.assertEqual(rc, 0)
            rendered = buffer.getvalue()
            self.assertIn("Ainda não há briefing registrado hoje", rendered)
            self.assertIn("Rodar o briefing agora", rendered)
            self.assertIn("prumo briefing", rendered)

    def test_canonical_workspace_with_wrappers_is_not_misclassified_as_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "CLAUDE.md").write_text("# wrapper\n", encoding="utf-8")
            (workspace / "AGENTS.md").write_text("# wrapper\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
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
            (state_dir / "briefing-state.json").write_text('{"last_briefing_at": ""}', encoding="utf-8")
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            args = Namespace(workspace=str(workspace), format="text")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_start(args)
            self.assertEqual(rc, 0)
            rendered = buffer.getvalue()
            self.assertNotIn("workspace legado", rendered)
            self.assertIn("o Prumo está de pé no workspace", rendered)

    def test_actions_keep_context_and_drop_google_placeholder_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
            (workspace / "PAUTA.md").write_text("# Pauta\n\n## Quente (precisa de atenção agora)\n\n- Incêndio no site\n", encoding="utf-8")
            (state_dir / "workspace-schema.json").write_text(
                json.dumps(
                    {
                        "user_name": "Batata",
                        "agent_name": "Prumo",
                        "timezone": "America/Sao_Paulo",
                        "briefing_time": "09:00",
                        "files": {
                            "generated": ["CLAUDE.md"],
                            "authorial": [],
                            "derived": ["_state/briefing-state.json"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            (state_dir / "briefing-state.json").write_text('{"last_briefing_at": ""}', encoding="utf-8")
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            args = Namespace(workspace=str(workspace), format="json")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_start(args)
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            action_ids = [action["id"] for action in payload["actions"]]
            self.assertIn("context", action_ids)
            self.assertTrue(any(action_id.startswith("auth-google") for action_id in action_ids))
            self.assertNotIn("auth-apple-reminders", action_ids)
            commands = " ".join(action["command"] for action in payload["actions"])
            self.assertNotIn("/caminho/do/client_secret.json", commands)
            self.assertLessEqual(len(payload["actions"]), 8)

    def test_google_auth_action_prefers_env_override_for_client_secrets(self) -> None:
        previous = os.environ.get("PRUMO_GOOGLE_CLIENT_SECRETS")
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "ws"
            state_dir = workspace / "_state"
            workspace.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            secrets_file = Path(tmpdir) / "custom-google-oauth.json"
            secrets_file.write_text("{}", encoding="utf-8")
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
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
            (state_dir / "briefing-state.json").write_text('{"last_briefing_at": ""}', encoding="utf-8")
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            os.environ["PRUMO_GOOGLE_CLIENT_SECRETS"] = str(secrets_file)
            try:
                args = Namespace(workspace=str(workspace), format="json")
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    rc = run_start(args)
            finally:
                if previous is None:
                    os.environ.pop("PRUMO_GOOGLE_CLIENT_SECRETS", None)
                else:
                    os.environ["PRUMO_GOOGLE_CLIENT_SECRETS"] = previous
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            commands = [action["command"] for action in payload["actions"]]
            self.assertTrue(any(str(secrets_file) in command for command in commands))

    def test_json_output_exposes_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text("> **prumo_version: 4.13.2**\n", encoding="utf-8")
            (workspace / "PAUTA.md").write_text("# Pauta\n\n## Em andamento\n\n- Projeto X\n", encoding="utf-8")
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
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            args = Namespace(workspace=str(workspace), format="json")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_start(args)
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["user_name"], "Batata")
            self.assertEqual(payload["adapter_contract_version"], "2026-03-21")
            self.assertEqual(payload["workspace_resolution"]["source"], "explicit")
            self.assertEqual(payload["adapter_hints"]["preferred_entrypoint"]["shell_command"], "prumo")
            self.assertEqual(
                payload["adapter_hints"]["briefing_structured_entrypoint"]["shell_command"],
                f"prumo briefing --workspace {workspace.resolve()} --refresh-snapshot --format json",
            )
            self.assertIn("Prumo", payload["adapter_hints"]["short_invocations"])
            self.assertIn("short_acceptance", payload["adapter_hints"]["behavior"])
            self.assertEqual(payload["platform"]["label"], platform_label())
            self.assertIn("daily_operation", payload)
            self.assertIn("next_move", payload)
            self.assertIn("selection_contract", payload)
            self.assertEqual(payload["selection_contract"]["accepts_next_move"], "briefing")
            self.assertIn("1", payload["selection_contract"]["accept_tokens"])
            self.assertTrue(payload["daily_operation"]["supports"])
            self.assertTrue(payload["daily_operation"]["conversation_rules"]["short_acceptance_executes_next_move"])
            self.assertIn("capabilities", payload)
            self.assertTrue(payload["capabilities"]["daily_operation"]["workflow_scaffolding"])
            self.assertTrue(payload["actions"])
            self.assertEqual(payload["actions"][0]["id"], "briefing")
            self.assertEqual(payload["actions"][0]["kind"], "shell")
            self.assertIn("shell_command", payload["actions"][0])
            continue_action = next(action for action in payload["actions"] if action["id"] == "continue")
            self.assertEqual(continue_action["kind"], "host-prompt")
            self.assertIn("documentation_targets", continue_action)
            self.assertIn("outcome", continue_action)
            align_core_action = next(action for action in payload["actions"] if action["id"] == "align-core")
            self.assertEqual(align_core_action["category"], "workspace-alignment")
            self.assertIn("prumo migrate --workspace", align_core_action["command"])
            self.assertFalse(any(action["id"] == "workflow-scaffold" for action in payload["actions"]))
            self.assertEqual(payload["next_move"]["id"], "briefing")

    def test_json_output_surfaces_inbox_processing_when_queue_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            inbox_dir = workspace / "Inbox4Mobile"
            state_dir.mkdir(parents=True, exist_ok=True)
            inbox_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
            (workspace / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
            (workspace / "INBOX.md").write_text("# Inbox\n\n- Item solto\n", encoding="utf-8")
            (inbox_dir / "_preview-index.json").write_text(
                json.dumps({"items": [{"filename": "item1.txt"}, {"filename": "item2.txt"}]}),
                encoding="utf-8",
            )
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
            yesterday = (
                datetime.now(ZoneInfo("America/Sao_Paulo")) - timedelta(days=1)
            ).replace(hour=9, minute=0, second=0, microsecond=0)
            (state_dir / "briefing-state.json").write_text(
                json.dumps({"last_briefing_at": yesterday.isoformat()}),
                encoding="utf-8",
            )
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            args = Namespace(workspace=str(workspace), format="json")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_start(args)
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            process_inbox = next(action for action in payload["actions"] if action["id"] == "process-inbox")
            self.assertEqual(process_inbox["category"], "inbox-triage")
            self.assertIn("documentation_targets", process_inbox)
            self.assertIn("fila que está encostada", process_inbox["label"])
            self.assertIn("host_prompt", process_inbox)
            self.assertNotIn("shell_command", process_inbox)

    def test_json_output_prefers_continue_when_day_already_started_and_item_is_hot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
            (workspace / "PAUTA.md").write_text(
                "# Pauta\n\n## Quente (precisa de atenção agora)\n\n- Fechar decisão do plano PME\n",
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
            same_day = datetime.now(ZoneInfo("America/Sao_Paulo")).replace(
                hour=9,
                minute=12,
                second=0,
                microsecond=0,
            )
            (state_dir / "briefing-state.json").write_text(
                json.dumps({"last_briefing_at": same_day.isoformat()}),
                encoding="utf-8",
            )
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            args = Namespace(workspace=str(workspace), format="json")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_start(args)
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["actions"][0]["id"], "continue")
            self.assertTrue(payload["actions"][0]["recommended"])
            self.assertEqual(payload["next_move"]["id"], "continue")

    def test_json_output_marks_workspace_resolution_from_cwd(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
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
            (state_dir / "briefing-state.json").write_text('{"last_briefing_at": ""}', encoding="utf-8")
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            os.chdir(workspace)
            try:
                args = Namespace(workspace=None, format="json")
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    rc = run_start(args)
            finally:
                os.chdir(previous_cwd)
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["workspace_resolution"]["source"], "cwd")
            self.assertEqual(
                payload["adapter_hints"]["structured_entrypoint"]["shell_command"],
                f"prumo start --workspace {workspace.resolve()} --format json",
            )


if __name__ == "__main__":
    unittest.main()
