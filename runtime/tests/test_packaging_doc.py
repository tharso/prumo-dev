"""#181 (M4 do épico #177): PACKAGING.md não pode apodrecer.

O doc declara onde cada artefato vive e quem sincroniza — este teste o
valida contra a realidade (plugin.json, árvore skills/, tabela de intenções
do CORE, marker do stub no código, pyproject) POR SEÇÃO E POR CÉLULA:
palavra certa no lugar errado não passa. Doc que mente quebra o CI.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "PACKAGING.md"
SKILLS = REPO_ROOT / "skills"
MODULES = SKILLS / "prumo" / "references" / "modules"
CORE = SKILLS / "prumo" / "references" / "prumo-core.md"


def _intent_modules_from_core() -> set[str]:
    """A lista canônica dos módulos de intenção é a tabela do CORE
    ('Manutenção sem comando próprio', #172) — o teste deriva de lá em vez
    de duplicar (review Codex do M4)."""
    text = CORE.read_text(encoding="utf-8")
    section = text.split("### Manutenção sem comando próprio", 1)[1].split("##", 1)[0]
    return set(re.findall(r"modules/([a-z-]+)\.md", section))


def _table_row(text: str, cell_contains: str) -> str:
    """Linha de tabela cujo needle está numa das DUAS primeiras células —
    cobre a tabela de superfícies (|#|Nome|...) e a de artefatos (|Nome|...)."""
    for line in text.splitlines():
        if line.strip().startswith("|") and cell_contains in "|".join(line.split("|")[1:3]):
            return line
    raise AssertionError(f"linha de tabela com {cell_contains!r} não encontrada")


class PackagingDocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = DOC.read_text(encoding="utf-8")
        cls.plugin_skills = {
            Path(entry).name
            for entry in json.loads((REPO_ROOT / "plugin.json").read_text())["skills"]
        }
        cls.tree_skills = {d.name for d in SKILLS.iterdir() if d.is_dir()}

    def test_doc_lives_at_repo_root_not_in_skills(self) -> None:
        self.assertTrue(DOC.exists())
        self.assertFalse((SKILLS / "PACKAGING.md").exists(), "em skills/ embarcaria no wheel/espelho")

    def test_plugin_json_matches_skills_tree(self) -> None:
        # Pré-condição do doc: as duas fontes reais batem entre si.
        self.assertEqual(self.plugin_skills, self.tree_skills)

    def test_skill_list_is_exactly_the_plugin_set(self) -> None:
        # Conjunto EXATO extraído da frase do doc — não busca global.
        match = re.search(
            r"\*\*Skills top-level \((\d+) — exatamente as do `plugin\.json`\):\*\*\s*(.+?)\. Aparecem",
            self.text,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "frase das skills top-level mudou de formato")
        count = int(match.group(1))
        listed = set(re.findall(r"`([a-z-]+)`", match.group(2)))
        self.assertEqual(listed, self.plugin_skills, "lista do doc ≠ plugin.json")
        self.assertEqual(count, len(self.plugin_skills))

    def test_intent_modules_derived_from_core(self) -> None:
        canonical = _intent_modules_from_core()
        self.assertTrue(canonical, "tabela de intenções do core vazia?")
        section = self.text.split("**Módulos de intenção", 1)[1].split("**Nota", 1)[0]
        listed = set(re.findall(r"`([a-z-]+)`", section)) & (canonical | self.tree_skills)
        self.assertEqual(listed, canonical, "módulos do doc ≠ tabela do core (#172)")
        for name in canonical:
            with self.subTest(module=name):
                self.assertTrue((MODULES / f"{name}.md").exists())
                self.assertNotIn(name, self.tree_skills, f"{name} virou skill top-level")

    def test_core_row_declares_stub_in_the_cell(self) -> None:
        row = _table_row(self.text, "prumo-core.md")
        self.assertIn("stub-ponteiro", row, "a CÉLULA do core não declara o stub")
        self.assertIn(".prumo/system/PRUMO-CORE.md", row)
        import sys

        sys.path.insert(0, str(REPO_ROOT / "runtime"))
        from prumo_runtime.templates import CORE_STUB_MARKER

        self.assertIn(CORE_STUB_MARKER, row, "marker da célula divergiu do código")

    def test_skills_row_and_wrappers_row_cells(self) -> None:
        skills_row = _table_row(self.text, "Skills top-level")
        self.assertIn(".prumo/skills/", skills_row)
        self.assertIn("install_skills", skills_row)
        wrappers_row = _table_row(self.text, "Wrappers da raiz")
        self.assertIn("minimal", wrappers_row)
        self.assertIn("blocos autorais preservados", wrappers_row)

    def test_five_layer_chain_is_explicit(self) -> None:
        # #190: as 5 camadas nomeadas uma a uma — colapsá-las apaga o drift
        # entre elos (review Codex do M4).
        section = self.text.split("cadeia de propagação em 5 camadas", 1)[1].split("##", 1)[0]
        for layer, anchor in (
            ("1.", "prumo-dev"),
            ("2.", "mirror"),
            ("3.", "marketplaces/"),
            ("4.", "cowork_plugins` é legado morto"),
            ("5.", "rpm/"),
        ):
            with self.subTest(layer=layer):
                row = next(
                    (l for l in section.splitlines() if l.strip().startswith(f"| {layer}")),
                    None,
                )
                self.assertIsNotNone(row, f"camada {layer} sumiu da subtabela")
                self.assertIn(anchor, row)

    def test_start_note_present_and_skill_really_absent(self) -> None:
        self.assertIn("`prumo start`", self.text)
        self.assertIn("#134", self.text)
        self.assertNotIn("start", self.tree_skills, "a skill start voltou — nota do doc mente")

    def test_wheel_bundle_mechanism_matches_pyproject(self) -> None:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("prumo_runtime/_bundled/skills", pyproject)
        row = _table_row(self.text, "Wheel")
        self.assertIn("force-include", row)
        self.assertIn("hatchling", row)

    def test_next_divergence_is_a_decision(self) -> None:
        rule = self.text.split("## A regra", 1)[1]
        self.assertIn("DECISIONS.md", rule)
        self.assertIn("decisão", rule)
        self.assertIn("test_packaging_doc.py", rule)

    def test_cited_synchronizers_exist(self) -> None:
        for path in (
            REPO_ROOT / ".github" / "workflows" / "mirror-to-prumo.yml",
            REPO_ROOT / "scripts" / "generate_adapter_templates.py",
        ):
            with self.subTest(path=path.name):
                self.assertTrue(path.exists(), f"sincronizador citado não existe: {path}")
                self.assertIn(path.name, self.text)


if __name__ == "__main__":
    unittest.main()
