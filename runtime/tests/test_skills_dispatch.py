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

    def test_parses_folded_strip_indicator(self) -> None:
        """YAML `>-` (folded + strip trailing newline) deve funcionar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_md = Path(tmpdir) / "SKILL.md"
            skill_md.write_text(
                "---\nname: edge\ndescription: >-\n"
                "  linha um\n  linha dois\n---\n",
                encoding="utf-8",
            )
            result = parse_skill_frontmatter(skill_md)
            self.assertEqual(result["name"], "edge")
            self.assertIn("linha um", result["description"])
            self.assertIn("linha dois", result["description"])

    def test_parses_literal_keep_indicator(self) -> None:
        """YAML `|+` (literal + keep trailing newlines) deve funcionar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_md = Path(tmpdir) / "SKILL.md"
            skill_md.write_text(
                "---\nname: lit\ndescription: |+\n"
                "  bloco literal\n---\n",
                encoding="utf-8",
            )
            result = parse_skill_frontmatter(skill_md)
            self.assertIn("bloco literal", result["description"])


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

    def test_pipe_in_name_and_description_is_escaped(self) -> None:
        """Pipe (`|`) em name ou description não pode quebrar a tabela Markdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "ws"
            skill_dir = workspace / ".prumo" / "skills" / "edge"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: edge|case\n"
                "description: Usa A | B para decidir\n---\n",
                encoding="utf-8",
            )
            block = build_skills_dispatch_block(workspace)
            # Pipe deve estar escapado com backslash
            self.assertIn("edge\\|case", block)
            self.assertIn("A \\| B", block)
            # Pipe cru (sem backslash antes) só deve aparecer como
            # delimitador de coluna da tabela, não dentro de conteúdo.
            for line in block.split("\n"):
                if line.startswith("| edge"):
                    # Não deve conter pipe cru sem backslash antes
                    # (exceto os 4 delimitadores de coluna)
                    self.assertNotIn("edge|case", line)
                    self.assertNotIn("A | B", line)

    def test_removed_skill_disappears_from_block(self) -> None:
        """Skill removida do filesystem não deve aparecer no dispatch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            block_before = build_skills_dispatch_block(workspace)
            self.assertIn("doctor", block_before)
            # Remover skill
            import shutil
            shutil.rmtree(workspace / ".prumo" / "skills" / "doctor")
            block_after = build_skills_dispatch_block(workspace)
            self.assertNotIn("doctor", block_after)


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


class RepairPreIssue90WrapperTests(unittest.TestCase):
    """Repair deve substituir wrapper pré-#90 sem duplicar conteúdo."""

    def test_repair_replaces_pre90_wrapper_without_duplication(self) -> None:
        """Wrapper gerado antes da #90 (sem managed block) deve ser substituído,
        não receber conteúdo duplicado com o antigo + novo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            claude_md = workspace / "CLAUDE.md"

            # Simular wrapper pré-#90: conteúdo Prumo sem managed block e
            # com instrução antiga "ative a skill"
            pre90_content = (
                '# Prumo Adapter — Test User\n\n'
                '> Compatibilidade para Claude/Cowork.\n\n'
                '## Porta curta\n\n'
                '1. Se o usuário disser "Prumo" cru, ative a skill '
                '`prumo:abrir`.\n\n'
                '## Instrução primária\n\n'
                '1. Leia `Prumo/AGENT.md`.\n\n'
                'Agente: **Prumo**\n'
            )
            claude_md.write_text(pre90_content, encoding="utf-8")

            # Repair deve substituir inteiro
            repair_workspace(workspace)

            content = claude_md.read_text(encoding="utf-8")
            # NÃO deve ter "ative a skill" (instrução antiga)
            self.assertNotIn("ative a skill", content.lower())
            # Deve ter dispatch dinâmico
            self.assertIn(".prumo/skills/abrir/SKILL.md", content)
            # NÃO deve ter header duplicado
            self.assertEqual(content.count("# Prumo Adapter"), 1)


class AgentRootDispatchTests(unittest.TestCase):
    """AGENT.md de raiz deve ter dispatch quando referencia tabela de skills."""

    def test_agent_root_has_dispatch_after_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = _make_test_workspace(Path(tmpdir))
            agent_md = workspace / "AGENT.md"
            self.assertTrue(agent_md.exists())
            content = agent_md.read_text(encoding="utf-8")
            # Se menciona "tabela de skills", deve ter o dispatch
            if "tabela de skills" in content:
                self.assertIn("## Skills disponíveis", content)
            # Deve ter paths de skills
            self.assertIn(".prumo/skills/abrir/SKILL.md", content)


if __name__ == "__main__":
    unittest.main()
