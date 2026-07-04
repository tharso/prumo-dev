"""Testes determinísticos da suíte de conformidade (#157, A0).

Estes testes NÃO invocam LLM. Provam duas coisas em CI, sem custo nem
flakiness:

1. **Os oráculos discriminam** — para cada cenário e cada caso, a gravação
   `compliant` dá PASS e a `violation` dá FAIL. Um oráculo que passasse os dois
   (ou reprovasse os dois) seria um oráculo cego; isto pega isso.
2. **O runner funciona ponta a ponta** — monta a fixture, aplica a execução
   (replay), roda o oráculo, decide. É o mesmo caminho do host real; só o passo
   de invocação do agente é trocado pela gravação determinística.

A invocação do agente real (`claude -p`) é o passo de cadência, rodado pelo
dono num shell autenticado — ver `conformance/SPEC.md`. Não roda aqui.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from conformance.harness import run, scenarios  # noqa: E402


class ConformanceHarnessTests(unittest.TestCase):
    def test_ha_pelo_menos_tres_cenarios_filesystem_safety(self) -> None:
        ids = {s.id for s in scenarios.SCENARIOS}
        self.assertGreaterEqual(len(ids), 3, "A0 exige ≥3 cenários")
        self.assertIn("c3_diario", ids)
        self.assertIn("c5_inbox_removal", ids)
        self.assertIn("c7_setup_diario", ids)

    def test_cada_cenario_tem_fixture_versionada(self) -> None:
        for sc in scenarios.SCENARIOS:
            with self.subTest(scenario=sc.id):
                self.assertTrue(
                    sc.fixture_dir.is_dir(),
                    f"fixture ausente para {sc.id}: {sc.fixture_dir}",
                )

    def test_oraculos_discriminam_compliant_de_violation(self) -> None:
        """O coração da A0: par negativo/positivo em cada caso, via runner."""
        for sc in scenarios.SCENARIOS:
            for case in sc.cases:
                with self.subTest(scenario=sc.id, variant=case.variant):
                    compliant = run.run_case_replay(sc, case, "compliant")
                    self.assertTrue(
                        compliant.verdict.ok,
                        f"{sc.id}/{case.variant}: agente compliant deveria PASSAR "
                        f"— {compliant.verdict.reason}",
                    )
                    violation = run.run_case_replay(sc, case, "violation")
                    self.assertFalse(
                        violation.verdict.ok,
                        f"{sc.id}/{case.variant}: agente violation deveria FALHAR "
                        f"— {violation.verdict.reason}",
                    )

    def test_runner_all_replay_fecha_verde(self) -> None:
        """`run --scenario all` no host replay conclui com sucesso (pipeline ok)."""
        with contextlib.redirect_stdout(io.StringIO()):
            rc = run.main(["--scenario", "all", "--host", "replay", "--replay", "both"])
        self.assertEqual(rc, 0, "o runner replay não fechou verde")

    def test_c3_tem_par_negativo_e_positivo(self) -> None:
        """O contrato do diário exige a direção de segurança (neg) além da feliz (pos)."""
        c3 = scenarios.by_id("c3_diario")
        variants = {c.variant for c in c3.cases}
        self.assertEqual(variants, {"neg", "pos"})


if __name__ == "__main__":
    unittest.main()
