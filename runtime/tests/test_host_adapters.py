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

    def test_manifest_valid_json_wrong_shape_no_crash(self) -> None:
        """Manifest que é JSON válido mas shape errada (ex: []) não causa crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            manifest_path = workspace / MANIFEST_RELATIVE
            # Escrever JSON válido mas com shape errada
            manifest_path.write_text("[]")
            result = repair_host_adapters(workspace)
            self.assertEqual(result["status"], "created from scratch")
            data = json.loads(manifest_path.read_text())
            self.assertEqual(data["version"], "1.0")

    def test_copy_repair_new_skill_registers_in_manifest(self) -> None:
        """Em fallback copy, repair de skill nova deve registrá-la no manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            from unittest.mock import patch
            with patch("prumo_runtime.host_adapters.os.symlink", side_effect=OSError("no symlink")):
                create_host_adapters(workspace)
            # Adicionar skill nova que não existia antes
            new_skill = workspace / ".prumo" / "skills" / "faxina"
            new_skill.mkdir()
            (new_skill / "SKILL.md").write_text("# faxina")
            # Repair com symlink falhando (copy mode)
            with patch("prumo_runtime.host_adapters.os.symlink", side_effect=OSError("no symlink")):
                repair_host_adapters(workspace)
            # A nova skill deve estar no manifest
            manifest_path = workspace / MANIFEST_RELATIVE
            data = json.loads(manifest_path.read_text())
            faxina_entries = [a for a in data["adapters"] if a["skill"] == "faxina"]
            self.assertTrue(len(faxina_entries) > 0)
            # E o adapter deve existir no filesystem
            self.assertTrue((workspace / ".claude" / "skills" / "faxina").is_dir())

    def test_unmanaged_dir_not_registered_in_manifest_after_repair(self) -> None:
        """Repair que precisa atualizar manifest não deve incluir dirs não-gerenciados."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            # Adicionar skill nova em .prumo/skills
            new_skill = workspace / ".prumo" / "skills" / "custom"
            new_skill.mkdir()
            (new_skill / "SKILL.md").write_text("# custom")
            # Criar diretório real (não-gerenciado) no host path CLAUDE
            host_custom = workspace / ".claude" / "skills" / "custom"
            host_custom.mkdir()
            (host_custom / "USER_FILE.md").write_text("user data")
            # Quebrar um adapter existente pra forçar needs_manifest_update
            link = workspace / ".claude" / "skills" / "briefing"
            link.unlink()
            link.symlink_to("/nonexistent/path")
            repair_host_adapters(workspace)
            # O dir não-gerenciado no host CLAUDE não deve estar no manifest
            manifest_path = workspace / MANIFEST_RELATIVE
            data = json.loads(manifest_path.read_text())
            claude_custom = [
                a for a in data["adapters"]
                if a["skill"] == "custom" and a["host"] == "claude"
            ]
            self.assertEqual(len(claude_custom), 0)
            # Mas o conteúdo do usuário deve estar intacto
            self.assertTrue((host_custom / "USER_FILE.md").exists())
            # E uma chamada subsequente de create_host_adapters não deve destruí-lo
            create_host_adapters(workspace)
            self.assertTrue((host_custom / "USER_FILE.md").exists())

    def test_manifest_malformed_adapters_field_no_crash(self) -> None:
        """Manifest com adapters malformado não causa crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            manifest_path = workspace / MANIFEST_RELATIVE
            bad_manifests = [
                '{"adapters": null}',
                '{"adapters": "bad"}',
                '{"adapters": [{"bad": 1}]}',
                '{"adapters": [{"host": "claude", "skill": []}]}',
                '{"adapters": [{"host": "", "skill": "x"}]}',
                '{"adapters": [{"host": 123, "skill": "x"}]}',
            ]
            for bad_value in bad_manifests:
                manifest_path.write_text(bad_value)
                result = repair_host_adapters(workspace)
                self.assertIn(result["status"], ("ok", "created from scratch"),
                              f"Failed for: {bad_value}")
            data = json.loads(manifest_path.read_text())
            self.assertEqual(data["version"], "1.0")

    def test_create_with_malformed_manifest_and_existing_dir(self) -> None:
        """create_host_adapters com manifest malformado e dir real existente não crasha."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)
            # Criar dir real não-gerenciado
            host_custom = workspace / ".claude" / "skills" / "briefing"
            # Adicionar uma nova skill pra forçar o path do _is_unmanaged
            new_skill = workspace / ".prumo" / "skills" / "extra"
            new_skill.mkdir()
            (new_skill / "SKILL.md").write_text("# extra")
            # Corromper manifest com shape inválida
            manifest_path = workspace / MANIFEST_RELATIVE
            manifest_path.write_text('{"adapters": [{"host": "claude", "skill": []}]}')
            # Não deve crashar
            result = create_host_adapters(workspace)
            self.assertIsInstance(result["adapters_created"], int)


class StaleManifestProtectionTests(unittest.TestCase):
    """#89 Finding 3: create_host_adapters não deve sobrescrever dir real
    do usuário mesmo que o manifest stale diga 'managed'."""

    def test_create_preserves_user_dir_replacing_managed_symlink(self) -> None:
        """Se o usuário substituiu um symlink gerenciado por dir real com conteúdo
        customizado, create_host_adapters deve preservar o dir do usuário."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            # Primeira criação — adapters normais (symlinks)
            create_host_adapters(workspace)
            adapter = workspace / ".claude" / "skills" / "briefing"
            self.assertTrue(adapter.is_symlink())

            # Usuário substitui o symlink por um diretório real com conteúdo custom
            adapter.unlink()
            adapter.mkdir()
            custom_file = adapter / "CUSTOM.md"
            custom_file.write_text("# Meu briefing customizado")

            # Segunda chamada de create — NÃO deve destruir o dir do usuário
            result = create_host_adapters(workspace)
            self.assertIn(".claude/skills/briefing", result["skipped"])
            self.assertTrue(custom_file.exists(), "conteúdo customizado do usuário deve sobreviver")
            self.assertEqual(custom_file.read_text(), "# Meu briefing customizado")

    def test_create_preserves_user_dir_even_with_manifest_entry(self) -> None:
        """Mesmo que o manifest registre o par (host, skill) como gerenciado,
        se o path atual é dir real, create não deve destruir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)
            create_host_adapters(workspace)

            # Substitui symlink por dir real
            adapter = workspace / ".claude" / "skills" / "briefing"
            adapter.unlink()
            adapter.mkdir()
            (adapter / "MY_STUFF.md").write_text("usuário")

            # Manifest ainda tem a entrada antiga — stale
            manifest_path = workspace / MANIFEST_RELATIVE
            manifest = json.loads(manifest_path.read_text())
            has_entry = any(
                e["host"] == "claude" and e["skill"] == "briefing"
                for e in manifest.get("adapters", [])
            )
            self.assertTrue(has_entry, "manifest deve ter a entrada antes do teste")

            # create_host_adapters NÃO deve confiar no manifest stale
            result = create_host_adapters(workspace)
            self.assertTrue(
                (adapter / "MY_STUFF.md").exists(),
                "dir real do usuário não pode ser destruído por manifest stale",
            )


    def test_repair_preserves_user_dir_in_copy_mode_with_version_drift(self) -> None:
        """Codex review: repair_host_adapters() com copy mode + manifest stale
        (runtime_version defasado) não deve destruir dir real do usuário."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _setup_workspace(tmpdir)

            # Forçar copy mode (simula ambiente sem symlink)
            from unittest.mock import patch
            with patch("prumo_runtime.host_adapters.os.symlink", side_effect=OSError("no symlink")):
                create_host_adapters(workspace)

            adapter = workspace / ".claude" / "skills" / "briefing"
            self.assertTrue(adapter.is_dir())
            self.assertFalse(adapter.is_symlink())

            # Usuário substitui a cópia gerenciada por dir próprio (sem marcador)
            import shutil
            shutil.rmtree(adapter)
            adapter.mkdir()
            (adapter / "MY_STUFF.md").write_text("dados do usuário")

            # Envenenar manifest pra simular drift de versão
            manifest_path = workspace / MANIFEST_RELATIVE
            manifest = json.loads(manifest_path.read_text())
            for entry in manifest.get("adapters", []):
                if entry["host"] == "claude" and entry["skill"] == "briefing":
                    entry["runtime_version"] = "0.0.0"
            manifest_path.write_text(json.dumps(manifest))

            # Repair NÃO deve destruir o dir do usuário
            with patch("prumo_runtime.host_adapters.os.symlink", side_effect=OSError("no symlink")):
                result = repair_host_adapters(workspace)

            self.assertTrue(
                (adapter / "MY_STUFF.md").exists(),
                "repair não pode destruir dir real do usuário em copy mode com drift",
            )


if __name__ == "__main__":
    unittest.main()
