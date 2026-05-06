"""
Testes de host adapters (#85).

Cobre: criação de symlinks, manifest, fallback copy, repair de
adapters quebrados, idempotência.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from prumo_runtime.host_adapters import (
    create_host_adapters,
    repair_host_adapters,
    HOST_CONVENTIONS,
    MANIFEST_RELATIVE,
)


def _setup_workspace(tmpdir: str) -> Path:
    """Cria workspace mínimo com skills em .prumo/skills/."""
    workspace = Path(tmpdir)
    skills_root = workspace / ".prumo" / "skills"
    for name in ("briefing", "start", "doctor"):
        skill_dir = skills_root / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\nSkill content.")
    return workspace


class CreateHostAdaptersTests(unittest.TestCase):
    def test_creates_claude_skill_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            result = create_host_adapters(workspace)
            claude_skills = workspace / ".claude" / "skills"
            self.assertTrue(claude_skills.exists())
            for name in ("briefing", "start", "doctor"):
                adapter = claude_skills / name
                self.assertTrue(adapter.is_symlink())
                self.assertTrue(adapter.resolve().is_dir())
                self.assertTrue((adapter / "SKILL.md").exists())
            self.assertIn("claude", result["hosts_created"])

    def test_symlinks_are_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            link = workspace / ".claude" / "skills" / "briefing"
            target = os.readlink(str(link))
            self.assertFalse(os.path.isabs(target))
            self.assertIn(".prumo", target)

    def test_creates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            manifest_path = workspace / MANIFEST_RELATIVE
            self.assertTrue(manifest_path.exists())
            data = json.loads(manifest_path.read_text())
            self.assertEqual(data["version"], "1.0")
            self.assertTrue(len(data["adapters"]) > 0)
            adapter = data["adapters"][0]
            self.assertIn("host", adapter)
            self.assertIn("skill", adapter)
            self.assertIn("mode", adapter)
            self.assertEqual(adapter["mode"], "symlink")

    def test_idempotent_does_not_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            create_host_adapters(workspace)
            manifest_path = workspace / MANIFEST_RELATIVE
            data = json.loads(manifest_path.read_text())
            skills_count = len([a for a in data["adapters"] if a["host"] == "claude"])
            self.assertEqual(skills_count, 3)

    def test_no_skills_no_adapters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / ".prumo" / "skills").mkdir(parents=True)
            result = create_host_adapters(workspace)
            self.assertEqual(result["adapters_created"], 0)

    def test_fallback_copy_when_symlink_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            from unittest.mock import patch
            with patch("prumo_runtime.host_adapters.os.symlink", side_effect=OSError("no symlink")):
                result = create_host_adapters(workspace)
            claude_skills = workspace / ".claude" / "skills"
            for name in ("briefing", "start", "doctor"):
                adapter = claude_skills / name
                self.assertTrue(adapter.is_dir())
                self.assertFalse(adapter.is_symlink())
                self.assertTrue((adapter / "SKILL.md").exists())
            manifest_path = workspace / MANIFEST_RELATIVE
            data = json.loads(manifest_path.read_text())
            self.assertTrue(any(a["mode"] == "copy" for a in data["adapters"]))

    def test_hosts_flag_limits_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            result = create_host_adapters(workspace, hosts=["claude"])
            self.assertIn("claude", result["hosts_created"])
            self.assertFalse((workspace / ".agent" / "skills").exists())


class RepairHostAdaptersTests(unittest.TestCase):
    def test_repairs_broken_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            # Quebrar um symlink
            link = workspace / ".claude" / "skills" / "briefing"
            link.unlink()
            link.symlink_to("/nonexistent/path")
            result = repair_host_adapters(workspace)
            self.assertTrue(result["repaired"] > 0)
            self.assertTrue(link.resolve().is_dir())

    def test_recreates_missing_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            # Remover um adapter
            link = workspace / ".claude" / "skills" / "start"
            link.unlink()
            result = repair_host_adapters(workspace)
            self.assertTrue(result["repaired"] > 0)
            self.assertTrue(link.exists())

    def test_no_manifest_creates_from_scratch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            result = repair_host_adapters(workspace)
            manifest_path = workspace / MANIFEST_RELATIVE
            self.assertTrue(manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
