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


class AutoralTriggerTest(unittest.TestCase):
    """Gatilho `sempre (autoral)` (#241): conta quando presente; ausência é
    tolerada (mapa deletado pelo usuário ≠ instalação quebrada); `sempre` puro
    segue fail-closed."""

    SKILL = "\n".join(
        [
            "# Briefing",
            "",
            "## Mapa de carregamento por fase",
            "",
            "| Fase | Gatilho | Arquivo | Seção | Tipo |",
            "|---|---|---|---|---|",
            "| F0 | sempre | `CLAUDE.md` | (integral) | wrapper |",
            "| F0 | sempre | `Prumo/AGENT.md` | (integral) | porta |",
            "| F0 | sempre (autoral) | `Prumo/Agente/MAPA-AUTORAL.md` | (integral) | autoral |",
            "",
        ]
    )

    def _measure(self, *, with_autoral: bool) -> dict:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".prumo" / "skills" / "briefing").mkdir(parents=True)
            (ws / ".prumo" / "skills" / "briefing" / "SKILL.md").write_text(
                self.SKILL, encoding="utf-8"
            )
            (ws / "CLAUDE.md").write_text("wrapper de quatro palavras", encoding="utf-8")
            (ws / "AGENTS.md").write_text("wrapper pior perfil aqui", encoding="utf-8")
            (ws / "Prumo").mkdir()
            (ws / "Prumo" / "AGENT.md").write_text("porta com três", encoding="utf-8")
            if with_autoral:
                (ws / "Prumo" / "Agente").mkdir()
                (ws / "Prumo" / "Agente" / "MAPA-AUTORAL.md").write_text(
                    "# Mapa autoral\n\n- `Escrita/` — contrato próprio\n", encoding="utf-8"
                )
            return audit.measure(ws)

    def test_autoral_presente_conta_no_cesto(self) -> None:
        report = self._measure(with_autoral=True)
        item = next(i for i in report["items"] if "MAPA-AUTORAL" in i["file"])
        self.assertTrue(item["exists"])
        self.assertGreater(item["words"], 0)
        self.assertFalse([e for e in report["errors"] if "MAPA-AUTORAL" in e])

    def test_autoral_ausente_e_tolerado_sem_erro(self) -> None:
        report = self._measure(with_autoral=False)
        item = next(i for i in report["items"] if "MAPA-AUTORAL" in i["file"])
        self.assertFalse(item["exists"])
        self.assertEqual(item["words"], 0)
        self.assertIn("tolerado", item["note"])
        self.assertFalse([e for e in report["errors"] if "MAPA-AUTORAL" in e])

    def test_sempre_puro_ausente_continua_fail_closed(self) -> None:
        skill = self.SKILL.replace("sempre (autoral)", "sempre")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".prumo" / "skills" / "briefing").mkdir(parents=True)
            (ws / ".prumo" / "skills" / "briefing" / "SKILL.md").write_text(skill, encoding="utf-8")
            (ws / "CLAUDE.md").write_text("wrapper de quatro palavras", encoding="utf-8")
            (ws / "AGENTS.md").write_text("wrapper pior perfil aqui", encoding="utf-8")
            (ws / "Prumo").mkdir()
            (ws / "Prumo" / "AGENT.md").write_text("porta com três", encoding="utf-8")
            report = audit.measure(ws)
        self.assertTrue(
            [e for e in report["errors"] if "MAPA-AUTORAL" in e and "ausente" in e],
            f"`sempre` puro ausente deveria ser erro — errors={report['errors']}",
        )


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
        rows, invalid = audit.parse_manifest(self.SKILL)
        self.assertEqual(invalid, [])
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["file"], "Prumo/AGENT.md")
        self.assertEqual(rows[1]["section"], "até: # Parte 2 — Playbooks operacionais")
        self.assertEqual(rows[2]["section"], "## Guardrails")

    def test_no_manifest_returns_none(self) -> None:
        self.assertIsNone(audit.parse_manifest("# Briefing\n\nsem mapa\n"))

    def test_five_cells_with_empty_required_field_is_invalid(self) -> None:
        # Codex série r3: cinco células com campo obrigatório vazio passava.
        skill = self.SKILL.replace(
            "| F1 | sempre | `.prumo/system/PRUMO-CORE.md` | `## Guardrails` | instrução |",
            "| F1 |  | `.prumo/system/PRUMO-CORE.md` | `## Guardrails` | instrução |",
        )
        rows, invalid = audit.parse_manifest(skill)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(invalid), 1)

    def test_extra_column_is_invalid(self) -> None:
        # r4: len != 5 exato — coluna extra também é linha inválida.
        skill = self.SKILL.replace(
            "| F0 | sempre | `Prumo/AGENT.md` | (integral) | instrução |",
            "| F0 | sempre | `Prumo/AGENT.md` | (integral) | instrução | extra |",
        )
        rows, invalid = audit.parse_manifest(skill)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(invalid), 1)

    def test_partially_malformed_line_is_reported_not_swallowed(self) -> None:
        # Codex série r2: linha inválida engolida = subcontagem silenciosa
        # com o resto válido.
        skill = self.SKILL.replace(
            "| F1 | sempre | `.prumo/system/PRUMO-CORE.md` | `## Guardrails` | instrução |",
            "| F1 | sempre | faltando células |",
        )
        rows, invalid = audit.parse_manifest(skill)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(invalid), 1)
        self.assertIn("faltando células", invalid[0])


class SandboxMeasurementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="prumo-audit-test-")
        cls.ws = audit.build_sandbox(Path(cls._tmp.name))
        cls.report = audit.measure(cls.ws)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_manifest_mode_on_current_skill(self) -> None:
        # #180: o SKILL instalado declara o mapa fásico — o audit flipa
        # sozinho pro modo manifest.
        self.assertEqual(self.report["mode"], "manifest")

    def test_basket_has_f0_f1_always_items(self) -> None:
        # O cesto do modo manifest = linhas F0/F1 com gatilho `sempre` do
        # mapa (#180). Módulos condicionais (canais, montagem, update...)
        # ficam FORA do cesto por design.
        files = [item["file"] for item in self.report["items"]]
        modules = ".prumo/skills/prumo/references/modules"
        for expected in (
            "CLAUDE.md",
            "Prumo/AGENT.md",
            ".prumo/system/PRUMO-CORE.md",
            ".prumo/skills/briefing/SKILL.md",
            f"{modules}/briefing-procedure.md",
            "Prumo/Agente/PERFIL.md",
            "Prumo/Agente/ROTINA.md",
            "Prumo/Agente/PESSOAS.md",
            f"{modules}/briefing-estado.md",
            f"{modules}/version-preflight.md",
        ):
            with self.subTest(file=expected):
                self.assertIn(expected, files)
        for excluded in (
            f"{modules}/briefing-canais.md",
            f"{modules}/briefing-montagem.md",
            f"{modules}/version-update.md",
            f"{modules}/load-policy.md",
        ):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, files)

    def test_dispatch_esta_no_cesto(self) -> None:
        # #248: o dispatch.md (1.189w) é leitura obrigatória da abertura via
        # opening_reads do AGENT.md — fora do cesto ele era gasto invisível
        # ("dieta por esconder o bolo atrás da balança", Codex [P1-8]).
        files = [item["file"] for item in self.report["items"]]
        self.assertIn(".prumo/skills/prumo/references/modules/dispatch.md", files)

    def test_toda_leitura_de_abertura_esta_no_manifesto(self) -> None:
        # #248, fechamento da CLASSE: qualquer arquivo .md que o AGENT.md
        # gerado mande ler na ABERTURA tem de estar no cesto F0/F1 `sempre` —
        # um opening_read novo fora do manifesto quebra aqui, não vira gasto
        # invisível de novo.
        import re
        agent = (self.ws / "Prumo" / "AGENT.md").read_text(encoding="utf-8")
        lines = agent.splitlines()
        anchor = next(i for i, ln in enumerate(lines) if "você já está lendo" in ln)
        opening: list[str] = []
        for ln in lines[anchor:]:
            if ln.lstrip().startswith("#"):
                break
            opening.append(ln)
        numbered = [ln for ln in opening if re.match(r"\s*\d+\.\s", ln)]
        self.assertTrue(numbered, "âncora da abertura não rendeu linha numerada — template mudou?")
        basket = {item["file"] for item in self.report["items"]}
        for ln in numbered:
            paths = re.findall(r"`([^`]+\.md)`", ln)
            with self.subTest(line=ln.strip()[:70]):
                # Codex (#250 r1): linha de abertura da qual não se extrai
                # EXATAMENTE um path deixaria o guard da classe cego a ela —
                # item novo tem de vir com o arquivo entre crases.
                self.assertEqual(
                    len(paths),
                    1,
                    f"linha de abertura sem path extraível único: {ln.strip()!r}",
                )
                path = paths[0]
                path = path[2:] if path.startswith("./") else path
                if path == "AGENT.md":  # o item 1 é o próprio arquivo, já contado como Prumo/AGENT.md
                    continue
                self.assertIn(
                    path,
                    basket,
                    f"leitura de abertura fora do cesto F0/F1 `sempre`: {path}",
                )

    def test_core_is_staged_not_integral(self) -> None:
        # F0 lê o core ATÉ a Parte 2; a seção Guardrails entra em F1 — o
        # integral (2.4k+) nunca volta ao cesto em silêncio.
        core_items = [i for i in self.report["items"] if i["file"].endswith("PRUMO-CORE.md")]
        sections = {i["section"] for i in core_items}
        self.assertEqual(len(core_items), 2)
        self.assertTrue(any(s.startswith("até:") for s in sections), sections)
        self.assertNotIn("(integral)", sections)

    def test_worst_profile_swaps_wrapper_for_agents_full(self) -> None:
        # #180 PR11b: o teto do gate mede o pior perfil (host sem registry
        # entra por AGENTS.md full) — a folga do CLAUDE.md minimal não pode
        # mascarar regressão nos módulos.
        report = self.report
        self.assertIsInstance(report["worst_profile_total"], int)
        claude_words = sum(i["words"] for i in report["items"] if i["file"] == "CLAUDE.md")
        agents_words = report["worst_profile_wrapper_words"]
        self.assertGreater(agents_words, claude_words, "AGENTS full tem que pesar mais que o minimal")
        self.assertEqual(
            report["worst_profile_total"],
            report["total_before_first_user_data"] - claude_words + agents_words,
        )

    def test_manifest_without_claude_entry_is_error_not_common_profile(self) -> None:
        # Review Codex (PR11b): sem CLAUDE.md no cesto, "sem pior perfil"
        # aprovaria pelo perfil comum — tem que ser erro (rc 2).
        skill_path = self.ws / ".prumo" / "skills" / "briefing" / "SKILL.md"
        original = skill_path.read_text(encoding="utf-8")
        try:
            skill_path.write_text(
                original.replace("| F0 | sempre | `CLAUDE.md` | (integral) | wrapper da raiz |\n", ""),
                encoding="utf-8",
            )
            report = audit.measure(self.ws)
            self.assertIsNone(report["worst_profile_total"])
            self.assertTrue(any("exatamente 1" in e for e in report["errors"]))
            rc = audit.main(["--workspace", str(self.ws), "--json"])
            self.assertEqual(rc, 2)
        finally:
            skill_path.write_text(original, encoding="utf-8")

    def test_worst_profile_fails_closed_without_agents(self) -> None:
        agents = self.ws / "AGENTS.md"
        backup = agents.read_text(encoding="utf-8")
        try:
            agents.unlink()
            report = audit.measure(self.ws)
            self.assertIsNone(report["worst_profile_total"])
            self.assertTrue(any("AGENTS.md ausente" in e for e in report["errors"]))
        finally:
            agents.write_text(backup, encoding="utf-8")

    def test_ceiling_gates_on_worst_profile(self) -> None:
        # Teto entre o perfil comum e o pior → tem que ESTOURAR (rc=1).
        common = self.report["total_before_first_user_data"]
        worst = self.report["worst_profile_total"]
        between = (common + worst) // 2
        rc = audit.main(["--workspace", str(self.ws), "--ceiling", str(between), "--json"])
        self.assertEqual(rc, 1)
        rc_ok = audit.main(["--workspace", str(self.ws), "--ceiling", str(worst), "--json"])
        self.assertEqual(rc_ok, 0)

    def test_legacy_mode_still_works_without_manifest(self) -> None:
        # Compat: SKILL sem o heading do mapa → modo legacy com a rota fixa.
        skill_path = self.ws / ".prumo" / "skills" / "briefing" / "SKILL.md"
        original = skill_path.read_text(encoding="utf-8")
        try:
            skill_path.write_text(
                original.replace(audit.MANIFEST_HEADING, "## Mapa desligado"),
                encoding="utf-8",
            )
            report = audit.measure(self.ws)
            self.assertEqual(report["mode"], "legacy")
            files = [item["file"] for item in report["items"]]
            self.assertIn(
                ".prumo/skills/prumo/references/modules/briefing-procedure.md", files
            )
        finally:
            skill_path.write_text(original, encoding="utf-8")

    def test_sandbox_route_has_no_errors(self) -> None:
        self.assertEqual(self.report["errors"], [])

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
        words, exists, note, error = audit.resolve_words(
            self.ws, "Prumo/Agente/NAO-EXISTE.md", "(integral)"
        )
        self.assertEqual((words, exists, error), (0, False, False))
        self.assertIn("ausente", note)

    def test_missing_section_is_an_error(self) -> None:
        # Fail-closed: seção declarada que não existe num arquivo presente é
        # erro de rota, nunca zero silencioso (Codex série r1).
        words, exists, note, error = audit.resolve_words(
            self.ws, "Prumo/AGENT.md", "## Seção Que Não Existe"
        )
        self.assertEqual((words, exists, error), (0, True, True))
        self.assertIn("ausente", note)

    def test_reduction_pct_math(self) -> None:
        total = self.report["total_before_first_user_data"]
        expected = round(100 * (1 - total / audit.REFERENCE_WORDS), 1)
        self.assertEqual(self.report["reduction_pct_vs_reference"], expected)


class FailClosedTest(unittest.TestCase):
    def test_empty_manifest_is_error_not_zero_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            skill = ws / ".prumo" / "skills" / "briefing" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "# Briefing\n\n## Mapa de carregamento por fase\n\nsem tabela aqui\n",
                encoding="utf-8",
            )
            report = audit.measure(ws)
        self.assertEqual(report["mode"], "manifest")
        self.assertTrue(report["errors"], "manifesto vazio passou sem erro")

    def test_manifest_with_missing_section_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            skill = ws / ".prumo" / "skills" / "briefing" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "\n".join(
                    [
                        "# Briefing",
                        "",
                        "## Mapa de carregamento por fase",
                        "",
                        "| Fase | Gatilho | Arquivo | Seção | Tipo |",
                        "|---|---|---|---|---|",
                        "| F0 | sempre | `Prumo/AGENT.md` | `## Não Existe` | instrução |",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "Prumo").mkdir()
            (ws / "Prumo" / "AGENT.md").write_text("# AGENT\n\numas palavras\n", encoding="utf-8")
            report = audit.measure(ws)
        self.assertTrue(any("ausente" in e for e in report["errors"]))

    def test_legacy_missing_mandatory_files_are_errors(self) -> None:
        # Codex série r3: instalação quebrada (rota mandatória ausente) não
        # pode medir "zero" e passar — é erro nos DOIS modos.
        with tempfile.TemporaryDirectory() as tmp:
            report = audit.measure(Path(tmp))
        self.assertEqual(report["mode"], "legacy")
        missing = [e for e in report["errors"] if "rota mandatória ausente" in e]
        self.assertEqual(
            len(missing),
            len(audit.LEGACY_ROUTE),
            f"cada item ausente da rota deve virar um erro: {len(missing)}/{len(audit.LEGACY_ROUTE)}",
        )

    def test_main_returns_2_on_errors_even_with_generous_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            skill = ws / ".prumo" / "skills" / "briefing" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "# Briefing\n\n## Mapa de carregamento por fase\n\nsem tabela\n",
                encoding="utf-8",
            )
            rc = audit.main(["--workspace", str(ws), "--json", "--ceiling", "999999"])
        self.assertEqual(rc, 2, "rota quebrada não pode passar no teto")




class PortaVersusManifestoTest(unittest.TestCase):
    """#228 fase 2 (Codex, diff r1): se a porta manda ler o arquivo INTEIRO e o
    manifesto conta só uma fatia, a balança pesa menos do que o agente paga —
    isso é maquiar o instrumento. As duas declarações têm de bater."""

    def test_limite_do_dispatch_bate_entre_porta_e_manifesto(self) -> None:
        import tempfile
        from pathlib import Path as _P
        with tempfile.TemporaryDirectory() as tmp:
            ws = audit.build_sandbox(_P(tmp))
            porta = (ws / "Prumo" / "AGENT.md").read_text(encoding="utf-8")
            skill = (ws / ".prumo" / "skills" / "briefing" / "SKILL.md").read_text(encoding="utf-8")
        rows, _ = audit.parse_manifest(skill)
        f0 = [r for r in rows if r["file"].endswith("dispatch.md") and r["trigger"].lower() == "sempre"]
        self.assertEqual(len(f0), 1, "dispatch deveria ter UMA linha F0 no manifesto")
        secao = f0[0]["section"]
        self.assertTrue(secao.startswith("até: "), f"F0 do dispatch não é parcial: {secao!r}")
        marcador = secao[len("até: "):].strip()
        # a porta tem de declarar o MESMO limite pro agente
        linha = [ln for ln in porta.splitlines() if "dispatch.md" in ln]
        self.assertTrue(linha, "a porta não cita o dispatch na abertura")
        self.assertIn(
            marcador,
            linha[0],
            "a porta manda ler o dispatch sem o limite que o manifesto contabiliza",
        )


if __name__ == "__main__":
    unittest.main()
