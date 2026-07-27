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
    """A lista canônica dos módulos de intenção vem do PARSER canônico do
    runtime (`parse_intent_modules`, #183) sobre o core real — sem regex
    paralela nem lista duplicada (review Codex do M4, r2)."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "runtime"))
    from prumo_runtime.command_table import parse_intent_modules

    entries = parse_intent_modules(CORE.read_text(encoding="utf-8"))
    return {Path(entry["module"]).stem for entry in entries}


def _artifact_cells(text: str, artifact_contains: str) -> dict[str, str]:
    """Células NOMEADAS da linha da tabela de artefatos — asserção por
    coluna: valor certo na coluna errada não passa (review Codex, r2)."""
    lines = text.split("## Artefato → superfície → forma → sincronizador", 1)[1].splitlines()
    header = next(l for l in lines if l.strip().startswith("|"))
    columns = [
        c.strip().replace("**", "").replace("`", "")
        for c in header.strip().strip("|").split("|")
    ]
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) == len(columns) and artifact_contains in cells[0]:
            return dict(zip(columns, cells))
    raise AssertionError(f"linha de artefato com {artifact_contains!r} não encontrada")


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

    def test_intent_modules_exact_nominal_list(self) -> None:
        canonical = _intent_modules_from_core()
        self.assertTrue(canonical, "tabela de intenções do core vazia?")
        # A lista NOMINAL da frase do doc (entre o rótulo e "atendem"),
        # comparada como conjunto EXATO — módulo inventado no doc quebra
        # (interseção deixava `limpeza` passar; review Codex r2).
        match = re.search(
            r"\*\*Módulos de intenção \(não são skills — #172\):\*\*\s*(.+?)\s+atendem",
            self.text,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "frase dos módulos de intenção mudou de formato")
        listed = set(re.findall(r"`([a-z-]+)`", match.group(1)))
        self.assertEqual(listed, canonical, "lista nominal do doc ≠ parser canônico do core")
        for name in canonical:
            with self.subTest(module=name):
                self.assertTrue((MODULES / f"{name}.md").exists())
                self.assertNotIn(name, self.tree_skills, f"{name} virou skill top-level")

    def test_core_row_declares_stub_in_workspace_column(self) -> None:
        cells = _artifact_cells(self.text, "prumo-core.md")
        self.assertIn("stub-ponteiro", cells["Workspace"], "stub fora da coluna Workspace")
        self.assertIn(".prumo/system/PRUMO-CORE.md", cells["Workspace"])
        for surface in ("Source", "Espelho", "Store do host + conta", "Wheel _bundled"):
            self.assertIn("completo", cells[surface], f"core não é completo em {surface}")
        import sys

        sys.path.insert(0, str(REPO_ROOT / "runtime"))
        from prumo_runtime.templates import CORE_STUB_MARKER

        self.assertIn(CORE_STUB_MARKER, cells["Workspace"], "marker divergiu do código")

    def test_skills_and_wrappers_cells_by_column(self) -> None:
        skills = _artifact_cells(self.text, "Skills top-level")
        self.assertIn(".prumo/skills/", skills["Workspace"])
        self.assertIn("rpm/", skills["Store do host + conta"], "a materialização da conta sumiu da coluna")
        self.assertIn("install_skills", skills["Workspace"])
        self.assertIn("hatchling", skills["Wheel _bundled"])
        wrappers = _artifact_cells(self.text, "Wrappers da raiz")
        self.assertIn("minimal", wrappers["Workspace"], "perfil minimal fora da coluna Workspace")
        self.assertIn("blocos autorais preservados", wrappers["Workspace"])
        self.assertEqual(wrappers["Espelho"], "—")

    def test_five_layer_chain_is_explicit_and_exact(self) -> None:
        # #190: as 5 camadas nomeadas uma a uma — colapsá-las apaga o drift
        # entre elos (review Codex do M4). Exatamente 1..5, nada além.
        section = self.text.split("cadeia de propagação em 5 camadas", 1)[1].split("##", 1)[0]
        numbered = [
            l for l in section.splitlines()
            if re.match(r"\|\s*\d\.", l.strip())
        ]
        self.assertEqual(len(numbered), 5, "a subtabela tem que ter exatamente 5 camadas")
        for layer, anchor in (
            ("1.", "prumo-dev"),
            ("2.", "mirror"),
            ("3.", "marketplaces/"),
            ("4.", "cowork_plugins` é legado morto"),
            ("5.", "rpm/"),
        ):
            with self.subTest(layer=layer):
                row = next((l for l in numbered if l.strip().startswith(f"| {layer}")), None)
                self.assertIsNotNone(row, f"camada {layer} sumiu da subtabela")
                self.assertIn(anchor, row)
        # O circuito com o workspace fecha no elo 4 (plugin instalado), não 5.
        self.assertIn("**4→workspace**", section)

    def test_start_note_present_and_skill_really_absent(self) -> None:
        self.assertIn("`prumo start`", self.text)
        self.assertIn("#134", self.text)
        self.assertNotIn("start", self.tree_skills, "a skill start voltou — nota do doc mente")

    def test_wheel_bundle_mechanism_matches_pyproject(self) -> None:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("prumo_runtime/_bundled/skills", pyproject)
        surface_row = next(
            l for l in self.text.splitlines() if l.strip().startswith("| 4 |") and "Wheel" in l
        )
        self.assertIn("force-include", surface_row)
        self.assertIn("hatchling", surface_row)

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
