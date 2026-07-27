"""#181 (M4 do épico #177): PACKAGING.md não pode apodrecer.

O doc declara onde cada artefato vive e quem sincroniza — este teste o
valida contra a realidade (plugin.json + árvore skills/ + mecanismos que
ele cita). Doc que mente quebra o CI; mudança real exige atualizar o doc
no mesmo PR (e registrar no DECISIONS.md).
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "PACKAGING.md"
SKILLS = REPO_ROOT / "skills"
MODULES = SKILLS / "prumo" / "references" / "modules"

INTENT_MODULES = ("faxina", "sanitize", "doctor")


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
        self.assertFalse((SKILLS / "PACKAGING.md").exists(), "no skills/ seria vendorado")

    def test_plugin_json_matches_skills_tree(self) -> None:
        # Pré-condição do doc: as duas fontes reais batem entre si.
        self.assertEqual(self.plugin_skills, self.tree_skills)

    def test_doc_lists_every_plugin_skill(self) -> None:
        for skill in sorted(self.plugin_skills):
            with self.subTest(skill=skill):
                self.assertIn(f"`{skill}`", self.text, f"skill {skill} sumiu do doc")
        count = len(self.plugin_skills)
        self.assertIn(f"({count} — exatamente as do `plugin.json`)", self.text)

    def test_intent_modules_exist_and_are_not_top_level_skills(self) -> None:
        for name in INTENT_MODULES:
            with self.subTest(module=name):
                self.assertIn(f"`{name}`", self.text)
                self.assertTrue(
                    (MODULES / f"{name}.md").exists(),
                    f"módulo de intenção {name}.md não existe em modules/",
                )
                self.assertNotIn(
                    name,
                    self.tree_skills,
                    f"{name} virou skill top-level — contradiz o doc e a #172",
                )

    def test_vendored_core_declared_as_stub_and_marker_is_real(self) -> None:
        self.assertIn("stub-ponteiro", self.text)
        self.assertIn("<!-- prumo-core-stub: v1 -->", self.text)
        import sys

        sys.path.insert(0, str(REPO_ROOT / "runtime"))
        from prumo_runtime.templates import CORE_STUB_MARKER

        self.assertIn(CORE_STUB_MARKER, self.text, "marker do doc divergiu do código")

    def test_start_note_present_and_skill_really_absent(self) -> None:
        self.assertIn("`prumo start`", self.text)
        self.assertIn("#134", self.text)
        self.assertNotIn("start", self.tree_skills, "a skill start voltou — nota do doc mente")

    def test_wheel_bundle_mechanism_matches_pyproject(self) -> None:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("prumo_runtime/_bundled/skills", pyproject)
        self.assertIn("_bundled", self.text)
        self.assertIn("force-include", self.text)

    def test_next_divergence_is_a_decision(self) -> None:
        self.assertIn("DECISIONS.md", self.text)
        self.assertIn("decisão", self.text)
        self.assertIn("test_packaging_doc.py", self.text)

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
