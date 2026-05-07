"""
Testa geração do bloco de dispatch de skills no CLAUDE.md (#90).

O bloco é gerado automaticamente a partir do filesystem (.prumo/skills/)
e injetado nos wrappers via prumo setup/repair. Resolve o gap de discovery:
hosts como Cowork descobrem skills por plugin registry, não por filesystem.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from prumo_runtime.workspace import (
    WorkspaceConfig,
    create_missing_files,
    ensure_directories,
    install_skills,
    parse_skill_frontmatter,
    build_skills_dispatch_block,
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
    install_skills(workspace, layout_mode="nested")
    create_missing_files(config)
    return workspace


class ParseSkillFrontmatterTests(unittest.TestCase):
    """Mini-parser de frontmatter YAML simples (sem PyYAML)."""

    def test_parses_name_and_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_md = Path(tmpdir) / "SKILL.md"
            skill_md.write_text(
                "---\n"
                "name: briefing\n"
                "description: >\n"
                "  Morning briefing do Prumo. Executa a rotina completa.\n"
                "---\n"
                "\n# Conteudo\n",
                encoding="utf-8",
            )
            result = parse_skill_frontmatter(skill_md)
            self.assertEqual(result["name"], "briefing")
            self.assertIn("Morning briefing", result["description"])

    def test_parses_simple_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_md = Path(tmpdir) / "SKILL.md"
            skill_md.write_text(
                "---\nname: doctor\ndescription: Diagnostico\n---\n",
                encoding="utf-8",
            )
            result = parse_skill_frontmatter(skill_md)
            self.assertEqual(result["name"], "doctor")
            self.assertEqual(result["description"], "Diagnostico")

    def test_handles_missing_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_md = Path(tmpdir) / "SKILL.md"
            skill_md.write_text("# No frontmatter\n", encoding="utf-8")
            result = parse_skill_frontmatter(skill_md)
            self.assertEqual(result, {})

    def test_handles_nonexistent_file(self) -> None:
        result = parse_skill_frontmatter(Path("/nonexistent/SKILL.md"))
        self.assertEqual(result, {})


class BuildSkillsDispatchBlockTests(unittest.TestCase):
    """Geração do bloco de dispatch a partir do filesystem."""

    def test_generates_block_with_all_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            block = build_skills_dispatch_block(workspace)
            # Deve conter todas as skills do repo
            self.assertIn("abrir", block)
            self.assertIn("briefing", block)
            self.assertIn("doctor", block)
            self.assertIn(".prumo/skills/abrir/SKILL.md", block)
            self.assertIn(".prumo/skills/briefing/SKILL.md", block)

    def test_block_instructs_direct_file_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            block = build_skills_dispatch_block(workspace)
            # Deve instruir leitura direta, não uso de Skill tool
            self.assertIn("leia", block.lower())
            self.assertIn("SKILL.md", block)
            # NÃO deve dizer "ative a skill"
            self.assertNotIn("ative a skill", block)

    def test_empty_skills_returns_empty_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "empty-ws"
            workspace.mkdir()
            block = build_skills_dispatch_block(workspace)
            self.assertEqual(block, "")

    def test_new_skill_appears_in_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            # Adicionar skill fake
            fake_skill = workspace / ".prumo" / "skills" / "minha-skill"
            fake_skill.mkdir(parents=True)
            (fake_skill / "SKILL.md").write_text(
                "---\nname: minha-skill\ndescription: Skill de teste\n---\n",
                encoding="utf-8",
            )
            block = build_skills_dispatch_block(workspace)
            self.assertIn("minha-skill", block)
            self.assertIn("Skill de teste", block)


class SetupGeneratesDispatchTests(unittest.TestCase):
    """Setup deve gerar CLAUDE.md com dispatch block (skills instaladas antes)."""

    def test_claude_md_contains_dispatch_after_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            claude_md = workspace / "CLAUDE.md"
            self.assertTrue(claude_md.exists())
            content = claude_md.read_text(encoding="utf-8")
            # Deve ter o dispatch de skills
            self.assertIn(".prumo/skills/abrir/SKILL.md", content)
            self.assertIn(".prumo/skills/briefing/SKILL.md", content)
            # NÃO deve dizer "ative a skill"
            self.assertNotIn("ative a skill", content.lower())


class RepairUpdatesDispatchTests(unittest.TestCase):
    """Repair deve atualizar wrappers quando dispatch muda, mesmo sem drift."""

    def test_repair_adds_new_skill_to_claude_md_without_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            claude_md = workspace / "CLAUDE.md"
            content_before = claude_md.read_text(encoding="utf-8")

            # Adicionar skill fake
            fake_skill = workspace / ".prumo" / "skills" / "nova-skill"
            fake_skill.mkdir(parents=True)
            (fake_skill / "SKILL.md").write_text(
                "---\nname: nova-skill\ndescription: Skill adicionada\n---\n",
                encoding="utf-8",
            )

            # Repair sem drift de versão
            result = repair_workspace(workspace)

            content_after = claude_md.read_text(encoding="utf-8")
            self.assertIn("nova-skill", content_after)
            self.assertIn(".prumo/skills/nova-skill/SKILL.md", content_after)


if __name__ == "__main__":
    unittest.main()
