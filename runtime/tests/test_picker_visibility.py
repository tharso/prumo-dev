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
_DISABLE_RE = re.compile(r"(?m)^disable-model-invocation:\s*true\s*$")
_DESC_RE = re.compile(r"(?m)^description:")


def _frontmatter(text: str) -> str:
    """Bloco YAML entre o primeiro par de `---`. É o que o host lê — uma menção
    no CORPO do SKILL.md (exemplo, doc) não pode contar como configuração."""
    m = re.match(r"(?s)\s*---\n(.*?)\n---", text)
    return m.group(1) if m else ""


def _front(skill_dir: Path) -> str:
    return _frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))


def _is_hidden(skill_dir: Path) -> bool:
    return bool(_HIDDEN_RE.search(_front(skill_dir)))


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
            fm = _front(SKILLS_DIR / name)
            self.assertRegex(fm, _DESC_RE, f"{name} sem description no frontmatter (não seria invocável)")
            self.assertNotRegex(fm, _DISABLE_RE, f"{name} não pode cortar a invocação do agente")

    def test_only_frontmatter_counts(self):
        # Regressão (review Codex): uma linha YAML `user-invocable: false` no CORPO
        # (ex.: doc/exemplo de frontmatter) casaria no arquivo inteiro — o bug
        # antigo. Tem que NÃO contar; só o frontmatter conta.
        body_only = "---\nname: x\ndescription: y\n---\n\nExemplo de frontmatter:\nuser-invocable: false\n"
        self.assertRegex(body_only, _HIDDEN_RE)            # arquivo inteiro casaria (bug antigo)
        self.assertNotRegex(_frontmatter(body_only), _HIDDEN_RE)  # mas o frontmatter não → correto
        self.assertEqual(_frontmatter(body_only).strip(), "name: x\ndescription: y")
        in_front = "---\nname: x\nuser-invocable: false\n---\n\ncorpo\n"
        self.assertRegex(_frontmatter(in_front), _HIDDEN_RE)


if __name__ == "__main__":
    unittest.main()
