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
    install_skills,
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
            self.assertEqual(result.get("merged", []), [])
            backup_dir = workspace / ".prumo" / "backup"
            existing = list(backup_dir.glob("repair-version-bump-*"))
            self.assertEqual(existing, [])

    def test_repair_drifted_workspace_regenerates_system_and_canonical_files(self) -> None:
        # Sistema (PRUMO-CORE.md) e canonical do Prumo (Prumo/AGENT.md) entram em
        # `recreated`. Wrappers de raiz (CLAUDE.md, AGENTS.md, AGENT.md) NÃO devem
        # ser regenerados — eles entram em `merged` se tiver custom block, ou
        # ficam intactos se já estiverem em dia.
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            _force_core_version(workspace, "5.0.0")
            self.assertEqual(parse_core_version(workspace), "5.0.0")

            result = repair_workspace(workspace)

            self.assertIn("version_drift", result)
            self.assertEqual(result["version_drift"]["from"], "5.0.0")
            self.assertEqual(result["version_drift"]["to"], __version__)
            self.assertEqual(parse_core_version(workspace), __version__)
            self.assertIn("Prumo/AGENT.md", result["recreated"])
            self.assertIn(".prumo/system/PRUMO-CORE.md", result["recreated"])
            # Wrappers de raiz NÃO em "recreated" — eles foram preservados
            self.assertNotIn("CLAUDE.md", result["recreated"])
            self.assertNotIn("AGENTS.md", result["recreated"])
            self.assertNotIn("AGENT.md", result["recreated"])

    def test_repair_drifted_workspace_creates_backup_with_only_system_canonicals(self) -> None:
        # Backup deve conter SÓ PRUMO-CORE.md e Prumo/AGENT.md. Wrappers de raiz
        # NÃO entram no backup porque podem ter conteúdo autoral.
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
            # Wrappers de raiz NÃO no backup
            self.assertFalse((backup_root / "CLAUDE.md").exists())
            self.assertFalse((backup_root / "AGENTS.md").exists())
            self.assertFalse((backup_root / "AGENT.md").exists())

    def test_repair_writes_backup_under_canonical_backups_path(self) -> None:
        # Issue #81 P3.8: escritor de backup deve usar `.prumo/backups/<scope>/<timestamp>/`,
        # não `.prumo/backup/<scope>-<timestamp>/` (drift histórico). E backups legados
        # em `.prumo/backup/` se existirem devem permanecer intocados — sanitize cuida.
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            # Simula backup legado pre-existente no path antigo.
            legacy_backup = workspace / ".prumo" / "backup" / "legacy-thing-20260101T000000"
            legacy_backup.mkdir(parents=True, exist_ok=True)
            (legacy_backup / "marker.txt").write_text("legado preservado", encoding="utf-8")

            _force_core_version(workspace, "5.0.0")
            result = repair_workspace(workspace)

            # Novo backup foi criado em .prumo/backups/<scope>/<timestamp>/
            backup_root = Path(result["version_drift"]["backup_root"])
            self.assertIn(".prumo/backups/repair-version-bump/", str(backup_root))
            self.assertNotIn("/.prumo/backup/", str(backup_root))

            # Legado em .prumo/backup/ continua existindo, intocado
            self.assertTrue(legacy_backup.exists())
            self.assertEqual(
                (legacy_backup / "marker.txt").read_text(encoding="utf-8"),
                "legado preservado",
            )

    def test_repair_idempotent_after_drift_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            _force_core_version(workspace, "5.0.0")
            first = repair_workspace(workspace)
            self.assertIn("version_drift", first)

            second = repair_workspace(workspace)
            self.assertNotIn("version_drift", second)
            self.assertEqual(second["recreated"], [])
            self.assertEqual(second.get("merged", []), [])

    def test_repair_drift_preserves_authorial_content_in_root_wrappers(self) -> None:
        # CRITICAL: usuário pode ter customizado CLAUDE.md/AGENTS.md/AGENT.md fora
        # do bloco gerenciado. repair com drift deve preservar essa customização
        # byte-for-byte, atualizando apenas o bloco entre <!-- prumo:begin --> e
        # <!-- prumo:end -->. Codex review da #84 explicitou esse contrato.
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            claude_path = workspace / "CLAUDE.md"

            # Simula um CLAUDE.md autoral: cabeçalho personalizado + bloco prumo + cauda autoral
            claude_path.write_text(
                "# Meu CLAUDE.md customizado\n"
                "\n"
                "Notas pessoais que o Prumo nunca pode tocar.\n"
                "\n"
                "<!-- prumo:begin -->\n"
                "Bloco antigo do Prumo (será atualizado).\n"
                "<!-- prumo:end -->\n"
                "\n"
                "Mais notas autorais depois do bloco.\n",
                encoding="utf-8",
            )

            _force_core_version(workspace, "5.0.0")
            result = repair_workspace(workspace)

            self.assertIn("version_drift", result)
            self.assertIn("CLAUDE.md", result.get("merged", []))

            new_content = claude_path.read_text(encoding="utf-8")
            # Conteúdo autoral preservado byte-for-byte
            self.assertIn("# Meu CLAUDE.md customizado", new_content)
            self.assertIn("Notas pessoais que o Prumo nunca pode tocar.", new_content)
            self.assertIn("Mais notas autorais depois do bloco.", new_content)
            # Bloco prumo foi atualizado (não tem mais o texto antigo)
            self.assertNotIn("Bloco antigo do Prumo", new_content)
            # Bloco prumo está presente com a marca canônica
            self.assertIn("<!-- prumo:begin -->", new_content)
            self.assertIn("<!-- prumo:end -->", new_content)


class RepairSkillsRestorationTests(unittest.TestCase):
    """#89 Finding 1: repair deve restaurar skills ausentes em .prumo/skills/."""

    def _make_workspace_with_skills(self, parent: Path) -> Path:
        """Cria workspace completo com skills instaladas (simula prumo setup)."""
        workspace = _make_test_workspace(parent)
        install_skills(workspace, layout_mode="nested")
        return workspace

    def test_repair_restores_deleted_skill_in_prumo_skills(self) -> None:
        """Se uma skill é apagada de .prumo/skills/, repair_workspace deve restaurá-la."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._make_workspace_with_skills(Path(tmpdir))
            skills_root = workspace / ".prumo" / "skills"

            # Confirma que skills foram instaladas
            installed_before = sorted(d.name for d in skills_root.iterdir() if d.is_dir())
            self.assertIn("briefing", installed_before)

            # Apaga uma skill
            import shutil
            shutil.rmtree(skills_root / "briefing")
            self.assertFalse((skills_root / "briefing").exists())

            # Repair deve restaurar
            repair_workspace(workspace)
            self.assertTrue(
                (skills_root / "briefing").is_dir(),
                "repair_workspace deve restaurar skills ausentes em .prumo/skills/",
            )
            self.assertTrue(
                (skills_root / "briefing" / "SKILL.md").exists(),
                "skill restaurada deve ter SKILL.md",
            )

    def test_repair_restores_skill_and_fixes_broken_adapter(self) -> None:
        """Full path: skill apagada → repair restaura skill + conserta adapter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._make_workspace_with_skills(Path(tmpdir))
            skills_root = workspace / ".prumo" / "skills"

            # Cria adapters
            from prumo_runtime.host_adapters import create_host_adapters, repair_host_adapters
            create_host_adapters(workspace)

            # Confirma adapter funciona
            adapter = workspace / ".claude" / "skills" / "briefing"
            self.assertTrue(adapter.exists())
            self.assertTrue(adapter.resolve().exists(), "adapter deve apontar pra skill existente")

            # Apaga a skill — adapter fica quebrado
            import shutil
            shutil.rmtree(skills_root / "briefing")
            self.assertFalse(adapter.resolve().exists(), "adapter deve estar quebrado")

            # Repair do workspace + host adapters (simula run_repair)
            repair_workspace(workspace)
            adapter_result = repair_host_adapters(workspace)

            # Skill restaurada
            self.assertTrue((skills_root / "briefing").is_dir())
            # Adapter agora funciona
            self.assertTrue(
                adapter.resolve().exists(),
                "após repair, adapter deve apontar pra skill restaurada",
            )


if __name__ == "__main__":
    unittest.main()
