from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from prumo_runtime.cli import main
from prumo_runtime.commands.setup import (
    _is_interactive,
    ask_if_missing,
    prompt_choice,
)


class SetupCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        # Estes testes simulam terminal interativo (input mockado).
        # Sem este mock, o fix da #72 detectaria stdin nao-TTY e bloquearia.
        self._isatty_patch = patch(
            "prumo_runtime.commands.setup.sys.stdin.isatty",
            return_value=True,
        )
        self._isatty_patch.start()

    def tearDown(self) -> None:
        self._isatty_patch.stop()

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
                    "Vida Batata",
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
            self.assertIn("Etapa 1 de 4", rendered)
            self.assertIn("Etapa 2 de 4", rendered)
            self.assertIn("Etapa 3 de 4", rendered)
            self.assertIn("Etapa 4 de 4", rendered)
            self.assertIn("Entre no workspace e rode `prumo`", rendered)

            import json

            schema = json.loads(
                (workspace / ".prumo" / "state" / "workspace-schema.json").read_text(encoding="utf-8")
            )
            self.assertEqual(schema.get("workspace_name"), "Vida Batata")

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
                    "Casa Batata",
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

    def test_setup_refuses_to_run_on_existing_prumo_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "JaExiste"
            workspace.mkdir(parents=True)
            (workspace / ".prumo" / "state").mkdir(parents=True)
            (workspace / ".prumo" / "state" / "workspace-schema.json").write_text(
                "{}", encoding="utf-8"
            )
            buffer = io.StringIO()
            with patch(
                "builtins.input",
                side_effect=[
                    "Batata",
                    str(workspace),
                ],
            ):
                with redirect_stdout(buffer):
                    with self.assertRaises(SystemExit) as ctx:
                        main(["setup"])
            self.assertEqual(ctx.exception.code, 1)
            rendered = buffer.getvalue()
            self.assertIn("já tem um workspace do Prumo", rendered)
            self.assertIn("prumo repair", rendered)


class NonInteractiveStdinTests(unittest.TestCase):
    """Cobre o fix da #72: setup roda em CI ou stdin redirected sem EOFError."""

    def test_is_interactive_respects_PRUMO_NONINTERACTIVE_env(self) -> None:
        with patch.dict(os.environ, {"PRUMO_NONINTERACTIVE": "1"}, clear=False):
            self.assertFalse(_is_interactive())

    def test_prompt_choice_uses_default_when_stdin_not_tty(self) -> None:
        buffer = io.StringIO()
        with patch("prumo_runtime.commands.setup.sys.stdin.isatty", return_value=False):
            with redirect_stdout(buffer):
                result = prompt_choice(
                    "Escolha:", {"a": "Opcao A", "b": "Opcao B"}, default="a"
                )
        self.assertEqual(result, "a")
        self.assertIn("nao-interativo", buffer.getvalue())
        self.assertIn("'a'", buffer.getvalue())

    def test_prompt_choice_fails_when_stdin_not_tty_and_no_default(self) -> None:
        with patch("prumo_runtime.commands.setup.sys.stdin.isatty", return_value=False):
            with self.assertRaises(SystemExit) as ctx:
                with redirect_stdout(io.StringIO()):
                    prompt_choice("Escolha:", {"a": "A", "b": "B"})
        self.assertIn("nao-interativo", str(ctx.exception))

    def test_ask_if_missing_returns_value_without_consulting_stdin(self) -> None:
        # Quando o valor ja vem por flag CLI, stdin nao e consultado.
        with patch("prumo_runtime.commands.setup.sys.stdin.isatty", return_value=False):
            self.assertEqual(ask_if_missing("Tharso", "Como te chamo? "), "Tharso")

    def test_ask_if_missing_fails_when_stdin_not_tty_and_no_value(self) -> None:
        with patch("prumo_runtime.commands.setup.sys.stdin.isatty", return_value=False):
            with self.assertRaises(SystemExit) as ctx:
                ask_if_missing(None, "Como te chamo? ")
        self.assertIn("nao-interativo", str(ctx.exception))

    def test_setup_runs_with_all_flags_and_stdin_redirected(self) -> None:
        """Caso de aceite da #72: setup completa exit 0 com stdin redirecionado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "ws"
            buffer = io.StringIO()
            argv = [
                "setup",
                "--user-name", "CI",
                "--workspace", str(workspace),
                "--workspace-name", "CI Workspace",
                "--agent-name", "Prumo",
                "--timezone", "America/Sao_Paulo",
                "--briefing-time", "09:00",
            ]
            with patch("prumo_runtime.commands.setup.sys.stdin.isatty", return_value=False):
                with redirect_stdout(buffer):
                    rc = main(argv)
            self.assertEqual(rc, 0)
            self.assertTrue((workspace / ".prumo" / "state" / "workspace-schema.json").exists())
            rendered = buffer.getvalue()
            self.assertIn("nao-interativo", rendered)
