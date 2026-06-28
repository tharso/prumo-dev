"""Política de visibilidade do picker `/` (#132).

Trava quais skills aparecem como comando digitável (`user-invocable` ausente/true)
e quais são escondidas do picker mas seguem invocáveis pelo agente
(`user-invocable: false`). Evita que a lista volte a inchar sem decisão.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

# Front-line: comandos que o usuário digita no dia a dia (NÃO escondidos).
FRONT_LINE = {"briefing", "acervo", "fim", "menu", "prumo"}  # prumo == setup
# Escondidos do picker (mecânica do agente / ocasionais / onboarding redundante).
HIDDEN = {"abrir", "decidir", "faxina", "start", "doctor", "higiene", "sanitize"}

_HIDDEN_RE = re.compile(r"(?m)^user-invocable:\s*false\s*$")


def _is_hidden(skill_dir: Path) -> bool:
    return bool(_HIDDEN_RE.search((skill_dir / "SKILL.md").read_text(encoding="utf-8")))


class PickerVisibilityTests(unittest.TestCase):
    def test_classification_covers_all_skills(self):
        dirs = {d.name for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").exists()}
        self.assertEqual(dirs, FRONT_LINE | HIDDEN, "skill nova sem decisão de visibilidade no picker")

    def test_front_line_is_user_invocable(self):
        for name in FRONT_LINE:
            self.assertFalse(
                _is_hidden(SKILLS_DIR / name),
                f"{name} deveria aparecer no picker (sem user-invocable: false)",
            )

    def test_hidden_are_not_user_invocable(self):
        for name in HIDDEN:
            self.assertTrue(
                _is_hidden(SKILLS_DIR / name),
                f"{name} deveria estar escondido do picker (falta user-invocable: false)",
            )

    def test_hidden_still_model_invocable(self):
        # Esconder do picker não pode torná-las inalcançáveis: a description
        # (gatilho de invocação pelo agente) tem que continuar lá, e nenhuma pode
        # ter `disable-model-invocation: true` (isso as cortaria do agente).
        for name in HIDDEN:
            text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"(?m)^description:", f"{name} sem description (não seria invocável)")
            self.assertNotIn("disable-model-invocation: true", text, f"{name} não pode cortar a invocação do agente")


if __name__ == "__main__":
    unittest.main()
