"""Guards estruturais da skill `decidir` (Fase 1, issue #102).

Travam o que é fácil quebrar sem perceber: a garantia de que o template é
offline (nenhuma URL de rede), o registro da skill nos manifestos que listam
skills individualmente, e a presença dos arquivos canônicos.
"""

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "decidir"


class DecidirSkillStructureTests(unittest.TestCase):
    def test_canonical_files_exist(self):
        for rel in (
            "SKILL.md",
            "assets/template.html",
            "assets/Boliand.otf",
            "references/acoes-allowlist.md",
            "references/exemplos-de-cards.md",
        ):
            self.assertTrue((SKILL_DIR / rel).exists(), f"falta {rel}")

    def test_skill_md_declares_name_decidir(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^name:\s*decidir\s*$", "frontmatter name deve ser 'decidir'")

    def test_registered_in_individual_manifests(self):
        for manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            data = json.loads((REPO_ROOT / manifest).read_text(encoding="utf-8"))
            self.assertIn(
                "./skills/decidir",
                data.get("skills", []),
                f"`./skills/decidir` não registrado em {manifest}",
            )


class DecidirTemplateOfflineTests(unittest.TestCase):
    def test_template_has_no_network_urls(self):
        """O usuário abre o HTML offline (file://). Nenhuma URL de rede é permitida."""
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        hits = re.findall(r"https?://", html)
        self.assertEqual(hits, [], "template.html não pode conter URL de rede (offline)")

    def test_template_references_local_font(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        self.assertIn("url('Boliand.otf')", html, "fonte deve ser referenciada localmente")

    def test_report_schema_is_versioned(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        self.assertIn("prumo_decidir_report.v1", html, "relatório precisa do schema JSON versionado")


class DecidirContentAwareGuards(unittest.TestCase):
    """#109: ações por conteúdo, links ativos, sem 'virar referência' passivo, sem API externa."""

    def test_allowlist_is_content_aware(self):
        text = (SKILL_DIR / "references" / "acoes-allowlist.md").read_text(encoding="utf-8")
        self.assertIn("extract_transcript", text)  # gancho de vídeo (soft-hook)
        self.assertIn("Vídeo", text)  # subtipo por conteúdo, não só "item de inbox"
        # "virar referência" passivo morreu (era effect save_reference).
        self.assertNotIn("save_reference", text)

    def test_skill_offline_is_mechanics_only_and_no_external_api(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("ATIVOS", skill)  # links de conteúdo do usuário vêm ativos
        self.assertIn("sem API key", skill)  # extract_transcript não exige API do Google


if __name__ == "__main__":
    unittest.main()
