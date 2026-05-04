from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from prumo_runtime import __version__
from prumo_runtime.cli import main
from prumo_runtime.commands.migrate_skills import (
    STATE_ALREADY_MIGRATED,
    STATE_AMBIGUOUS,
    STATE_HAS_PRUMO_SKILLS,
    STATE_HAS_PRUMO_SKILLS_OLD,
    STATE_NO_SKILLS,
    detect_skills_state,
    log_architectural_op,
    relevant_decisions_summary,
)


def _bootstrap_workspace(tmp: Path, *, with_schema: bool = True) -> Path:
    """Cria estrutura mínima de workspace nested válida (sem skills)."""
    workspace = tmp / "ws"
    (workspace / "Prumo").mkdir(parents=True)
    (workspace / ".prumo" / "state").mkdir(parents=True)
    (workspace / ".prumo" / "system").mkdir(parents=True)
    (workspace / ".prumo" / "logs").mkdir(parents=True)

    (workspace / "Prumo" / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
    (workspace / "Prumo" / "INBOX.md").write_text("# Inbox\n", encoding="utf-8")
    (workspace / "Prumo" / "REGISTRO.md").write_text("# Registro\n", encoding="utf-8")
    (workspace / "Prumo" / "IDEIAS.md").write_text("# Ideias\n", encoding="utf-8")
    (workspace / ".prumo" / "system" / "PRUMO-CORE.md").write_text(
        f"> **prumo_version: {__version__}**\n", encoding="utf-8"
    )

    if with_schema:
        schema = {
            "schema_version": "1.0",
            "runtime_version": __version__,
            "layout_mode": "nested",
            "user_name": "Tester",
            "agent_name": "Prumo",
            "timezone": "America/Sao_Paulo",
            "briefing_time": "09:00",
            "workspace_name": "Test Workspace",
            "files": {"generated": [], "authorial": [], "derived": []},
        }
        (workspace / ".prumo" / "state" / "workspace-schema.json").write_text(
            json.dumps(schema), encoding="utf-8"
        )
        (workspace / ".prumo" / "state" / "last-briefing.json").write_text(
            '{"at": ""}', encoding="utf-8"
        )

    return workspace


def _populate_skills_dir(target: Path, skill_names: list[str] | None = None) -> None:
    """Cria estrutura de skills mínima na pasta target."""
    skill_names = skill_names or ["briefing", "prumo"]
    target.mkdir(parents=True, exist_ok=True)
    for name in skill_names:
        skill_dir = target / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")


class DetectSkillsStateTests(unittest.TestCase):
    def test_no_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            state, source = detect_skills_state(workspace)
            self.assertEqual(state, STATE_NO_SKILLS)
            self.assertIsNone(source)

    def test_already_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / ".prumo" / "skills")
            state, source = detect_skills_state(workspace)
            self.assertEqual(state, STATE_ALREADY_MIGRATED)
            self.assertIsNone(source)

    def test_has_prumo_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / "Prumo" / "skills")
            state, source = detect_skills_state(workspace)
            self.assertEqual(state, STATE_HAS_PRUMO_SKILLS)
            self.assertEqual(source, workspace / "Prumo" / "skills")

    def test_has_prumo_skills_old(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / "Prumo" / "skills_OLD")
            state, source = detect_skills_state(workspace)
            self.assertEqual(state, STATE_HAS_PRUMO_SKILLS_OLD)
            self.assertEqual(source, workspace / "Prumo" / "skills_OLD")

    def test_ambiguous_when_target_and_legacy_coexist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / ".prumo" / "skills")
            _populate_skills_dir(workspace / "Prumo" / "skills_OLD")
            state, source = detect_skills_state(workspace)
            self.assertEqual(state, STATE_AMBIGUOUS)
            self.assertIsNone(source)

    def test_ambiguous_when_two_legacies_coexist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / "Prumo" / "skills")
            _populate_skills_dir(workspace / "Prumo" / "skills_OLD")
            state, source = detect_skills_state(workspace)
            self.assertEqual(state, STATE_AMBIGUOUS)
            self.assertIsNone(source)


class IdempotencyTests(unittest.TestCase):
    """Cobre os caminhos de saída limpa: workspace já migrado, sem skills."""

    def test_already_migrated_returns_zero_without_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / ".prumo" / "skills")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["migrate-skills", "--workspace", str(workspace)])
            self.assertEqual(rc, 0)
            self.assertIn("já tem skills em `.prumo/skills/`", buffer.getvalue())
            self.assertTrue((workspace / ".prumo" / "skills" / "briefing").exists())
            self.assertFalse((workspace / "Prumo" / "skills").exists())

    def test_no_skills_returns_zero_with_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["migrate-skills", "--workspace", str(workspace)])
            self.assertEqual(rc, 0)
            self.assertIn("não tem skills locais", buffer.getvalue())

    def test_ambiguous_returns_one_without_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / ".prumo" / "skills")
            _populate_skills_dir(workspace / "Prumo" / "skills_OLD")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["migrate-skills", "--workspace", str(workspace)])
            self.assertEqual(rc, 1)
            self.assertIn("ambíguo", buffer.getvalue())
            # Nada moveu.
            self.assertTrue((workspace / "Prumo" / "skills_OLD").exists())
            self.assertTrue((workspace / ".prumo" / "skills").exists())


class WorkspaceValidationTests(unittest.TestCase):
    def test_returns_two_when_workspace_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ghost = Path(tmpdir) / "nao-existe"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["migrate-skills", "--workspace", str(ghost)])
            self.assertEqual(rc, 2)


class PreflightTests(unittest.TestCase):
    """Cobre o comportamento de confirmação e cancelamento."""

    def test_cancel_when_stdin_not_tty_and_no_yes_flag(self) -> None:
        """Em CI sem --yes, prompt_choice usa default 'b' (cancelar) → migração não acontece."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / "Prumo" / "skills_OLD")
            buffer = io.StringIO()
            with patch(
                "prumo_runtime.commands.setup.sys.stdin.isatty",
                return_value=False,
            ):
                with redirect_stdout(buffer):
                    rc = main(["migrate-skills", "--workspace", str(workspace)])
            self.assertEqual(rc, 0)
            self.assertIn("cancelada", buffer.getvalue().lower())
            # skills_OLD ainda lá. .prumo/skills/ não criado.
            self.assertTrue((workspace / "Prumo" / "skills_OLD").exists())
            self.assertFalse((workspace / ".prumo" / "skills").exists())

    def test_cancel_when_user_chooses_b_in_interactive_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / "Prumo" / "skills_OLD")
            buffer = io.StringIO()
            with patch(
                "prumo_runtime.commands.setup.sys.stdin.isatty",
                return_value=True,
            ):
                with patch("builtins.input", return_value="b"):
                    with redirect_stdout(buffer):
                        rc = main(["migrate-skills", "--workspace", str(workspace)])
            self.assertEqual(rc, 0)
            self.assertIn("cancelada", buffer.getvalue().lower())
            self.assertTrue((workspace / "Prumo" / "skills_OLD").exists())


class ExecutionTests(unittest.TestCase):
    """Cobre a migração efetiva quando confirmada."""

    def test_migrates_prumo_skills_old_with_yes_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / "Prumo" / "skills_OLD", ["briefing", "prumo", "doctor"])

            # Generated files que repair_workspace deve recriar.
            (workspace / "Prumo" / "AGENT.md").write_text("# stale\n", encoding="utf-8")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["migrate-skills", "--workspace", str(workspace), "--yes"])

            self.assertEqual(rc, 0)
            output = buffer.getvalue()
            self.assertIn("Migração concluída", output)
            self.assertIn("--yes informada", output)

            # Pasta nova existe e tem as skills.
            target = workspace / ".prumo" / "skills"
            self.assertTrue(target.is_dir())
            self.assertTrue((target / "briefing" / "SKILL.md").exists())
            self.assertTrue((target / "prumo" / "SKILL.md").exists())
            self.assertTrue((target / "doctor" / "SKILL.md").exists())

            # Pasta antiga sumiu.
            self.assertFalse((workspace / "Prumo" / "skills_OLD").exists())

            # Backup foi criado.
            backup_root = workspace / ".prumo" / "backup"
            backups = [d for d in backup_root.iterdir() if d.name.startswith("relocate-skills-")]
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "skills_OLD" / "briefing" / "SKILL.md").exists())

            # Log da operação foi gravado.
            log_path = workspace / ".prumo" / "logs" / "architectural-ops.log"
            self.assertTrue(log_path.exists())
            log_content = log_path.read_text(encoding="utf-8")
            self.assertIn("relocate-skills", log_content)
            self.assertIn("skills_OLD -> .prumo/skills/", log_content)

    def test_migrates_prumo_skills_with_yes_flag(self) -> None:
        """Caminho pro estado pré-#73 (Prumo/skills/ ainda existe)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            _populate_skills_dir(workspace / "Prumo" / "skills", ["briefing"])
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["migrate-skills", "--workspace", str(workspace), "--yes"])
            self.assertEqual(rc, 0)
            self.assertTrue((workspace / ".prumo" / "skills" / "briefing" / "SKILL.md").exists())
            self.assertFalse((workspace / "Prumo" / "skills").exists())


class ArchitecturalLogTests(unittest.TestCase):
    def test_log_appends_iso_timestamp_op_and_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _bootstrap_workspace(Path(tmpdir))
            log_architectural_op(workspace, "relocate-skills", "primeira linha")
            log_architectural_op(workspace, "relocate-skills", "segunda linha")
            log_path = workspace / ".prumo" / "logs" / "architectural-ops.log"
            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            for line in lines:
                # formato: ISO\trelocate-skills\tmensagem
                parts = line.split("\t")
                self.assertEqual(len(parts), 3)
                self.assertEqual(parts[1], "relocate-skills")
            self.assertIn("primeira linha", lines[0])
            self.assertIn("segunda linha", lines[1])


class DecisionsSummaryTests(unittest.TestCase):
    def test_returns_message_when_decisions_md_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_repo = Path(tmpdir)
            result = relevant_decisions_summary(empty_repo)
            self.assertIn("não encontrado", result)

    def test_extracts_entries_with_skills_topic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "DECISIONS.md").write_text(
                "# Decisões\n\n"
                "## 2026-05-04 — Skills moram em .prumo/\n\n"
                "**Tópicos:** workspace-layout, skills-distribution\n"
                "**Contexto:** ...\n\n"
                "## 2026-04-22 — Outra decisão sem relação\n\n"
                "**Tópicos:** unrelated\n"
                "**Contexto:** assunto qualquer.\n",
                encoding="utf-8",
            )
            result = relevant_decisions_summary(repo)
            self.assertIn("2026-05-04", result)
            self.assertIn("Skills", result)
            self.assertNotIn("2026-04-22", result)


if __name__ == "__main__":
    unittest.main()
