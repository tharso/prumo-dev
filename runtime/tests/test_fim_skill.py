"""Guards estruturais da skill `fim` (#126).

Trava os guardrails do contrato conservador no texto da skill — o /fim é
orquestração (markdown), então o teste garante que o contrato não regride:
compactação, cerca contra overlap com briefing, anti-handover (#68), e
suggest-não-executa.
"""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "fim"


class FimSkillStructureTests(unittest.TestCase):
    def test_skill_md_exists_and_named_fim(self):
        skill = SKILL_DIR / "SKILL.md"
        self.assertTrue(skill.exists(), "falta skills/fim/SKILL.md")
        text = skill.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^name:\s*fim\s*$")

    def test_registered_in_individual_manifests(self):
        for manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            data = json.loads((REPO_ROOT / manifest).read_text(encoding="utf-8"))
            self.assertIn(
                "./skills/fim",
                data.get("skills", []),
                f"`./skills/fim` não registrado em {manifest}",
            )


class FimConservativeContractTests(unittest.TestCase):
    def setUp(self):
        self.skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    def test_handles_compaction(self):
        self.assertIn("compacta", self.skill.lower())

    def test_fences_against_briefing_overlap(self):
        low = self.skill.lower()
        self.assertIn("last-briefing", low)        # não marca o briefing
        self.assertIn("calendário", low)           # não lê agenda
        self.assertTrue("email" in low or "gmail" in low)

    def test_anti_handover_68(self):
        low = self.skill.lower()
        self.assertIn("#68", low)
        self.assertIn("narrativ", low)             # sem artefato narrativo

    def test_suggests_not_executes(self):
        low = self.skill.lower()
        self.assertIn("nunca executar", low)       # higiene/sanitize só propostas
        self.assertIn("propõe", low)

    def test_writes_to_existing_channels(self):
        for ch in ("IDEIAS.md", "PAUTA.md", "REGISTRO.md"):
            self.assertIn(ch, self.skill)


if __name__ == "__main__":
    unittest.main()
