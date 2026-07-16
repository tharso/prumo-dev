"""Testes do scripts/briefing_route_audit.py (#178, épico #177)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "briefing_route_audit", REPO_ROOT / "scripts" / "briefing_route_audit.py"
)
audit = importlib.util.module_from_spec(_SPEC)
sys.modules["briefing_route_audit"] = audit
_SPEC.loader.exec_module(audit)


class SectionExtractionTest(unittest.TestCase):
    TEXT = "\n".join(
        [
            "# Título",
            "intro com quatro palavras aqui",
            "# Parte 2 — Playbooks",
            "## Guardrails",
            "regra um",
            "regra dois",
            "## Outra seção",
            "resto",
        ]
    )

    def test_extract_section_by_heading(self) -> None:
        section = audit.extract_section(self.TEXT, "## Guardrails")
        self.assertIn("regra um", section)
        self.assertIn("regra dois", section)
        self.assertNotIn("resto", section)

    def test_extract_section_stops_at_same_level(self) -> None:
        section = audit.extract_section(self.TEXT, "## Guardrails")
        self.assertNotIn("Outra seção", section)

    def test_extract_until_marker(self) -> None:
        sliced = audit.extract_until_marker(self.TEXT, "# Parte 2 — Playbooks")
        self.assertIn("intro", sliced)
        self.assertNotIn("Guardrails", sliced)

    def test_missing_heading_returns_none(self) -> None:
        self.assertIsNone(audit.extract_section(self.TEXT, "## Não existe"))
        self.assertIsNone(audit.extract_until_marker(self.TEXT, "# Nada"))


class ManifestParserTest(unittest.TestCase):
    SKILL = "\n".join(
        [
            "# Briefing",
            "",
            "## Mapa de carregamento por fase",
            "",
            "| Fase | Gatilho | Arquivo | Seção | Tipo |",
            "|---|---|---|---|---|",
            "| F0 | sempre | `Prumo/AGENT.md` | (integral) | instrução |",
            "| F0 | sempre | `.prumo/system/PRUMO-CORE.md` | até: # Parte 2 — Playbooks operacionais | instrução |",
            "| F1 | sempre | `.prumo/system/PRUMO-CORE.md` | `## Guardrails` | instrução |",
            "| F2 | se houver inbox | `.prumo/skills/prumo/references/modules/inbox-processing.md` | (integral) | instrução |",
            "",
            "## Outra seção",
        ]
    )

    def test_manifest_parses_rows(self) -> None:
        rows = audit.parse_manifest(self.SKILL)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["file"], "Prumo/AGENT.md")
        self.assertEqual(rows[1]["section"], "até: # Parte 2 — Playbooks operacionais")
        self.assertEqual(rows[2]["section"], "## Guardrails")

    def test_no_manifest_returns_none(self) -> None:
        self.assertIsNone(audit.parse_manifest("# Briefing\n\nsem mapa\n"))


class SandboxMeasurementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="prumo-audit-test-")
        cls.ws = audit.build_sandbox(Path(cls._tmp.name))
        cls.report = audit.measure(cls.ws)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_legacy_mode_on_current_skill(self) -> None:
        self.assertEqual(self.report["mode"], "legacy")

    def test_route_has_all_legacy_items(self) -> None:
        files = [item["file"] for item in self.report["items"]]
        self.assertIn("CLAUDE.md", files)
        self.assertIn(".prumo/system/PRUMO-CORE.md", files)
        self.assertIn(
            ".prumo/skills/prumo/references/modules/briefing-procedure.md", files
        )

    def test_total_is_substantial(self) -> None:
        # Sanidade: a rota atual carrega o core (2k+) e o procedure (2k+).
        self.assertGreater(self.report["total_before_first_user_data"], 4000)

    def test_sandbox_perfil_is_small_template_stub(self) -> None:
        # O setup materializa um PERFIL.md template enxuto; nos recibos
        # oficiais (M4) ele é semeado com ~1.256w sintéticas pra espelhar a
        # instância auditada. Aqui só garantimos que o item é contado.
        perfil = next(
            item for item in self.report["items"] if item["file"] == "Prumo/Agente/PERFIL.md"
        )
        self.assertTrue(perfil["exists"])
        self.assertLess(perfil["words"], 200)

    def test_missing_file_counts_zero_and_is_declared(self) -> None:
        words, exists, note = audit.resolve_words(
            self.ws, "Prumo/Agente/NAO-EXISTE.md", "(integral)"
        )
        self.assertEqual((words, exists), (0, False))
        self.assertIn("ausente", note)

    def test_reduction_pct_math(self) -> None:
        total = self.report["total_before_first_user_data"]
        expected = round(100 * (1 - total / audit.REFERENCE_WORDS), 1)
        self.assertEqual(self.report["reduction_pct_vs_reference"], expected)


if __name__ == "__main__":
    unittest.main()
