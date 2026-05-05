"""
Testa que `prumo repair` detecta drift de versão entre PRUMO-CORE.md do
workspace e o runtime instalado, e regenera arquivos canônicos com backup.

Origem: #84 (audit Codex em #81 P2 / sessão de validação da release 5.3.0).
Antes desse fix, repair só checava presença de arquivo, não conteúdo —
workspace ficava preso em versão antiga após `pip install --upgrade`.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from prumo_runtime import __version__
from prumo_runtime.workspace import (
    WorkspaceConfig,
    create_missing_files,
    detect_version_drift,
    ensure_directories,
    parse_core_version,
    repair_workspace,
)


def _make_test_workspace(parent: Path) -> Path:
    workspace = parent / "test-ws"
    config = WorkspaceConfig(
        workspace=workspace,
        user_name="Test User",
        agent_name="Prumo",
        timezone_name="America/Sao_Paulo",
        briefing_time="09:00",
        layout_mode="nested",
        workspace_name="Test Workspace",
    )
    ensure_directories(workspace)
    create_missing_files(config)
    return workspace


def _force_core_version(workspace: Path, version: str) -> None:
    """Reescreve `PRUMO-CORE.md` substituindo o header `prumo_version: X` pra simular drift."""
    core_path = workspace / ".prumo" / "system" / "PRUMO-CORE.md"
    text = core_path.read_text(encoding="utf-8")
    new_text = re.sub(
        r"prumo_version:\s*[0-9.]+",
        f"prumo_version: {version}",
        text,
        count=1,
    )
    core_path.write_text(new_text, encoding="utf-8")


class VersionDriftDetectionTests(unittest.TestCase):
    def test_returns_none_when_workspace_in_sync_with_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            self.assertIsNone(detect_version_drift(workspace))

    def test_returns_drift_tuple_when_workspace_behind(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            _force_core_version(workspace, "5.0.0")
            drift = detect_version_drift(workspace)
            self.assertIsNotNone(drift)
            self.assertEqual(drift, ("5.0.0", __version__))

    def test_returns_none_when_core_md_missing(self) -> None:
        # Caso patológico: drift indeterminado é tratado como "não há drift".
        # detect_missing reporta o arquivo ausente e repair_workspace recria.
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            (workspace / ".prumo" / "system" / "PRUMO-CORE.md").unlink()
            self.assertIsNone(detect_version_drift(workspace))


class RepairVersionDriftTests(unittest.TestCase):
    def test_repair_in_sync_workspace_does_not_create_backup_or_report_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            result = repair_workspace(workspace)
            self.assertNotIn("version_drift", result)
            self.assertEqual(result["recreated"], [])
            backup_dir = workspace / ".prumo" / "backup"
            existing = list(backup_dir.glob("repair-version-bump-*"))
            self.assertEqual(existing, [])

    def test_repair_drifted_workspace_regenerates_canonical_files_with_runtime_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            _force_core_version(workspace, "5.0.0")
            self.assertEqual(parse_core_version(workspace), "5.0.0")

            result = repair_workspace(workspace)

            self.assertIn("version_drift", result)
            self.assertEqual(result["version_drift"]["from"], "5.0.0")
            self.assertEqual(result["version_drift"]["to"], __version__)
            self.assertEqual(parse_core_version(workspace), __version__)
            # AGENT.md, CLAUDE.md, AGENTS.md também regenerados
            self.assertIn("Prumo/AGENT.md", result["recreated"])
            self.assertIn("CLAUDE.md", result["recreated"])
            self.assertIn("AGENTS.md", result["recreated"])

    def test_repair_drifted_workspace_creates_backup_with_old_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            _force_core_version(workspace, "5.0.0")
            old_core_text = (workspace / ".prumo" / "system" / "PRUMO-CORE.md").read_text(encoding="utf-8")

            result = repair_workspace(workspace)

            backup_root = Path(result["version_drift"]["backup_root"])
            self.assertTrue(backup_root.exists())
            backed_up_core = backup_root / ".prumo" / "system" / "PRUMO-CORE.md"
            self.assertTrue(backed_up_core.exists())
            self.assertEqual(backed_up_core.read_text(encoding="utf-8"), old_core_text)

    def test_repair_idempotent_after_drift_resolution(self) -> None:
        # Primeiro repair regenera. Segundo repair não deve detectar drift de novo.
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            _force_core_version(workspace, "5.0.0")
            first = repair_workspace(workspace)
            self.assertIn("version_drift", first)

            second = repair_workspace(workspace)
            self.assertNotIn("version_drift", second)
            self.assertEqual(second["recreated"], [])


if __name__ == "__main__":
    unittest.main()
