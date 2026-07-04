"""
Detecção proativa de defasagem no briefing (#158, épico #161).

Prova que staleness deixa de ser silenciosa: a severidade por distância de
versão é computada corretamente, o briefing expõe o sinal e escala um alerta
forte (o teste da "falha silenciosa"), e a coerência de skills pega o workspace
com skills faltando (a origem do "Habilidade desconhecida").
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from prumo_runtime import version_check
from prumo_runtime.commands.briefing import (
    build_briefing_degradation,
    check_skills_coherence,
)


class StalenessSeverityTests(unittest.TestCase):
    def test_em_dia_e_ok(self) -> None:
        st = version_check.compute_staleness("5.27.0", "5.27.0")
        self.assertEqual(st["severity"], "ok")

    def test_um_minor_atras_e_warning(self) -> None:
        st = version_check.compute_staleness("5.26.0", "5.27.0")
        self.assertEqual(st["severity"], "warning")
        self.assertEqual(st["minor_behind"], 1)

    def test_dois_minor_atras_e_alert(self) -> None:
        st = version_check.compute_staleness("5.25.0", "5.27.0")
        self.assertEqual(st["severity"], "alert")

    def test_salto_de_major_e_alert(self) -> None:
        st = version_check.compute_staleness("4.7.0", "5.1.0")
        self.assertEqual(st["severity"], "alert")

    def test_salto_de_major_nao_vaza_sentinela_99(self) -> None:
        """O caso real 4.7.0→5.x não pode dizer '99 versões atrás' pro usuário."""
        st = version_check.compute_staleness("4.7.0", "5.28.0")
        self.assertNotIn("99", st["reason"])
        self.assertIn("major", st["reason"].lower())
        self.assertIn("4.7.0", st["reason"])
        self.assertIn("5.28.0", st["reason"])

    def test_so_patch_atras_e_info(self) -> None:
        st = version_check.compute_staleness("5.27.0", "5.27.3")
        self.assertEqual(st["severity"], "info")

    def test_sem_remoto_e_unknown_nao_ok(self) -> None:
        """Sem versão pública checada, NÃO declarar 'em dia' — é unknown."""
        st = version_check.compute_staleness("5.27.0", None)
        self.assertEqual(st["severity"], "unknown")
        self.assertNotEqual(st["severity"], "ok")

    def test_versao_ilegivel_nao_quebra(self) -> None:
        st = version_check.compute_staleness("abc", "5.27.0")
        self.assertEqual(st["severity"], "unknown")


class DegradationTests(unittest.TestCase):
    def test_alerta_forte_quando_defasado(self) -> None:
        """Falha silenciosa vira alerta forte: severity alert → alerta level error."""
        deg = build_briefing_degradation(
            core_outdated=False,
            next_move=None,
            version_status={"severity": "alert", "reason": "2 versões atrás"},
        )
        ids = {a["id"]: a for a in deg["alerts"]}
        self.assertIn("version-behind", ids)
        self.assertEqual(ids["version-behind"]["level"], "error")
        self.assertEqual(deg["status"], "error")

    def test_em_dia_nao_gera_alerta_de_versao(self) -> None:
        deg = build_briefing_degradation(
            core_outdated=False, next_move=None,
            version_status={"severity": "ok"},
        )
        self.assertFalse(any(a["id"] == "version-behind" for a in deg["alerts"]))

    def test_unknown_nao_grita(self) -> None:
        """Sem remoto (unknown) não vira alerta forte — só warning/alert gritam."""
        deg = build_briefing_degradation(
            core_outdated=False, next_move=None,
            version_status={"severity": "unknown"},
        )
        self.assertFalse(any(a["id"] == "version-behind" for a in deg["alerts"]))

    def test_skills_ausentes_geram_alerta_repair(self) -> None:
        deg = build_briefing_degradation(
            core_outdated=False, next_move=None, skills_missing=["fim"],
        )
        ids = {a["id"] for a in deg["alerts"]}
        self.assertIn("skills-missing", ids)
        self.assertEqual(deg["status"], "error")


class SkillsCoherenceTests(unittest.TestCase):
    def test_pasta_ausente_nao_inventa_alarme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_skills_coherence(Path(tmp)), [])

    def test_skill_faltando_e_detectada(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            skills = ws / ".prumo" / "skills"
            # cria acervo e menu, mas NÃO fim → fim deve aparecer como faltando
            for name in ("acervo", "menu"):
                (skills / name).mkdir(parents=True)
                (skills / name / "SKILL.md").write_text("x", encoding="utf-8")
            missing = check_skills_coherence(ws)
            self.assertIn("fim", missing)
            self.assertNotIn("acervo", missing)

    def test_todas_presentes_sem_faltas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            skills = ws / ".prumo" / "skills"
            for name in ("fim", "acervo", "menu"):
                (skills / name).mkdir(parents=True)
                (skills / name / "SKILL.md").write_text("x", encoding="utf-8")
            self.assertEqual(check_skills_coherence(ws), [])


if __name__ == "__main__":
    unittest.main()
