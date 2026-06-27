"""Guards estruturais da skill `menu` (#130).

Trava: arquivos canônicos, registro nos manifestos, a pergunta proativa, e o
anti-drift — o manual deriva da tabela do prumo-core, que precisa ser parseável
e conter o próprio `/menu` (fonte única, sem segunda lista).
"""

import json
import unittest
from pathlib import Path

from prumo_runtime.menu import parse_command_table

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "menu"
CORE = REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md"


class MenuSkillStructureTests(unittest.TestCase):
    def test_skill_md_exists_and_named_menu(self):
        skill = SKILL_DIR / "SKILL.md"
        self.assertTrue(skill.exists(), "falta skills/menu/SKILL.md")
        self.assertRegex(skill.read_text(encoding="utf-8"), r"(?m)^name:\s*menu\s*$")

    def test_registered_in_individual_manifests(self):
        for manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            data = json.loads((REPO_ROOT / manifest).read_text(encoding="utf-8"))
            self.assertIn("./skills/menu", data.get("skills", []), f"`./skills/menu` ausente em {manifest}")

    def test_skill_closes_proactive(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("proativ", skill)
        self.assertIn("dúvida", skill)


class MenuAntiDriftTests(unittest.TestCase):
    """A fonte única é a tabela do prumo-core; ela tem que ser parseável e
    conter os comandos canônicos — incluindo o próprio /menu."""

    def test_core_command_table_parses(self):
        cmds = parse_command_table(CORE.read_text(encoding="utf-8"))
        commands = {c["command"] for c in cmds}
        # registro do próprio /menu + features recentes na fonte única
        for expected in ("/menu", "/setup", "/briefing", "/acervo", "/fim"):
            self.assertIn(expected, commands, f"{expected} ausente na tabela do prumo-core")
        self.assertGreaterEqual(len(cmds), 8)
        for c in cmds:
            self.assertTrue(c["description"], f"{c['command']} sem descrição na tabela")


if __name__ == "__main__":
    unittest.main()
