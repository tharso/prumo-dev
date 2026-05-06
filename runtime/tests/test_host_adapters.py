"""
Testes de host adapters (#85).

Cobre: criação de symlinks, manifest, fallback copy, repair de
adapters quebrados, idempotência, preservação de paths não-gerenciados,
versão drift em copy mode, manifest corrompido.
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

    def test_preserves_unmanaged_skill_directory(self) -> None:
        """Diretório real pré-existente não registrado no manifest é preservado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            claude_skills = workspace / ".claude" / "skills"
            claude_skills.mkdir(parents=True)
            # Criar diretório real (não symlink) com conteúdo do usuário
            user_skill = claude_skills / "briefing"
            user_skill.mkdir()
            (user_skill / "MY_CUSTOM.md").write_text("User content")
            result = create_host_adapters(workspace)
            # Diretório do usuário preservado
            self.assertIn(".claude/skills/briefing", result["skipped"])
            self.assertTrue((user_skill / "MY_CUSTOM.md").exists())
            self.assertEqual(
                (user_skill / "MY_CUSTOM.md").read_text(), "User content"
            )

    def test_hosts_flag_preserves_other_hosts_in_manifest(self) -> None:
        """Chamar com hosts=['claude'] não apaga entries de antigravity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            # Criar adapters pra todos os hosts
            create_host_adapters(workspace)
            manifest_path = workspace / MANIFEST_RELATIVE
            data = json.loads(manifest_path.read_text())
            antigravity_count = len([
                a for a in data["adapters"] if a["host"] == "antigravity"
            ])
            self.assertTrue(antigravity_count > 0)
            # Re-criar apenas claude
            create_host_adapters(workspace, hosts=["claude"])
            data = json.loads(manifest_path.read_text())
            ag_after = len([
                a for a in data["adapters"] if a["host"] == "antigravity"
            ])
            self.assertEqual(ag_after, antigravity_count)

    def test_exact_relative_path_format(self) -> None:
        """Symlink target deve ser relativo com formato ../../.prumo/skills/X."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            link = workspace / ".claude" / "skills" / "briefing"
            target = os.readlink(str(link))
            # .claude/skills/briefing -> ../../.prumo/skills/briefing
            self.assertEqual(target, "../../.prumo/skills/briefing")


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

    def test_copy_mode_repairs_on_version_drift(self) -> None:
        """Copy mode adapter com runtime_version antiga é recriado no repair."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            from unittest.mock import patch
            with patch("prumo_runtime.host_adapters.os.symlink", side_effect=OSError("no symlink")):
                create_host_adapters(workspace)
            # Simular drift: alterar runtime_version no manifest
            manifest_path = workspace / MANIFEST_RELATIVE
            data = json.loads(manifest_path.read_text())
            for adapter in data["adapters"]:
                adapter["runtime_version"] = "0.0.0"
            manifest_path.write_text(json.dumps(data))
            # Repair deve detectar drift e reconstruir
            with patch("prumo_runtime.host_adapters.os.symlink", side_effect=OSError("no symlink")):
                result = repair_host_adapters(workspace)
            self.assertTrue(result["repaired"] > 0)

    def test_corrupted_manifest_handled_gracefully(self) -> None:
        """Manifest com JSON inválido não causa crash, recria do zero."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            # Corromper manifest
            manifest_path = workspace / MANIFEST_RELATIVE
            manifest_path.write_text("not valid json {{{")
            result = repair_host_adapters(workspace)
            self.assertEqual(result["status"], "created from scratch")
            # Manifest deve estar válido agora
            data = json.loads(manifest_path.read_text())
            self.assertEqual(data["version"], "1.0")

    def test_repair_preserves_unmanaged_directory(self) -> None:
        """Repair não destrói diretório real não registrado no manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            # Adicionar um diretório real não-gerenciado em outro skill slot
            new_skill = workspace / ".prumo" / "skills" / "custom"
            new_skill.mkdir()
            (new_skill / "SKILL.md").write_text("# custom")
            # Criar diretório real (não symlink) no host path
            host_custom = workspace / ".claude" / "skills" / "custom"
            host_custom.mkdir()
            (host_custom / "USER_FILE.md").write_text("user data")
            result = repair_host_adapters(workspace)
            # User file deve continuar intocado
            self.assertTrue((host_custom / "USER_FILE.md").exists())
            self.assertEqual(
                (host_custom / "USER_FILE.md").read_text(), "user data"
            )


if __name__ == "__main__":
    unittest.main()
