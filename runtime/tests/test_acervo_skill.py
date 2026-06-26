"""Guards estruturais da skill `acervo` (#125).

Travam o que é fácil quebrar sem perceber: template offline, fonte local,
schema versionado, sanitizador presente, os 3 verbos, a proveniência carregada
no relatório, o cross-check runtime↔template (campos do enumerador existem no
template) e o registro nos manifestos.
"""

import json
import re
import unittest
from pathlib import Path

from prumo_runtime.acervo import ITEM_FIELDS

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "acervo"
TEMPLATE = SKILL_DIR / "assets" / "template.html"


class AcervoSkillStructureTests(unittest.TestCase):
    def test_canonical_files_exist(self):
        for rel in (
            "SKILL.md",
            "assets/template.html",
            "assets/Boliand.otf",
            "references/acoes-acervo.md",
        ):
            self.assertTrue((SKILL_DIR / rel).exists(), f"falta {rel}")

    def test_skill_md_declares_name_acervo(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^name:\s*acervo\s*$")

    def test_registered_in_individual_manifests(self):
        for manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            data = json.loads((REPO_ROOT / manifest).read_text(encoding="utf-8"))
            self.assertIn(
                "./skills/acervo",
                data.get("skills", []),
                f"`./skills/acervo` não registrado em {manifest}",
            )


class AcervoTemplateOfflineTests(unittest.TestCase):
    def setUp(self):
        self.html = TEMPLATE.read_text(encoding="utf-8")

    def test_template_has_no_network_urls(self):
        hits = re.findall(r"https?://", self.html)
        self.assertEqual(hits, [], "template.html não pode conter URL de rede (offline)")

    def test_template_references_local_font(self):
        self.assertIn("url('Boliand.otf')", self.html)

    def test_report_schema_is_versioned(self):
        self.assertIn("prumo_acervo_report.v1", self.html)

    def test_sanitizer_and_escaper_present(self):
        self.assertIn("function safeUrl", self.html)
        self.assertIn("function escapeHtml", self.html)


class AcervoVerbsAndProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.html = TEMPLATE.read_text(encoding="utf-8")

    def test_three_fixed_verbs(self):
        for verb in ("include_pauta", "attack_now", "delete"):
            self.assertIn(verb, self.html, f"verbo {verb} ausente no template")

    def test_report_carries_full_provenance(self):
        # Sem proveniência completa no relatório, a remoção segura é impossível.
        for field in ("source_kind", "source_path", "anchor", "line_start", "line_end", "content_hash"):
            self.assertIn(field, self.html, f"relatório precisa carregar {field}")

    def test_runtime_item_fields_all_consumed_by_template(self):
        # Cross-check (Codex rodada 2): todo campo que o enumerador emite existe
        # no template. Trava drift entre o JSON do runtime e o HTML.
        for field in ITEM_FIELDS:
            self.assertIn(field, self.html, f"campo do enumerador `{field}` não aparece no template")

    def test_delete_archives_by_default(self):
        # "excluir" arquiva; deleção permanente só sob pedido explícito.
        self.assertIn("Arquivo/Acervo", self.html)
        self.assertIn("permanente", self.html.lower())
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("arquivar, não apagar", skill.lower())


if __name__ == "__main__":
    unittest.main()
