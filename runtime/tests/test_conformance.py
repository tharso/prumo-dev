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

from unittest import mock  # noqa: E402

from conformance.harness import hosts, run, scenarios  # noqa: E402


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

    def test_host_real_falha_fecha_fail_nao_falso_verde(self) -> None:
        """Se `claude -p` retorna non-zero, o veredito é FAIL — nunca roda o oráculo
        sobre workspace intocado (o falso verde que o Codex pegou)."""
        c7 = scenarios.by_id("c7_setup_diario")
        case = c7.cases[0]
        with mock.patch.object(hosts, "provision_skills", return_value="test"), \
             mock.patch.object(
                 hosts,
                 "run_claude_code",
                 return_value={"returncode": 1, "stdout": "", "stderr": "401 auth"},
             ):
            result = run.run_case_claude(c7, case, keep=False)
        self.assertFalse(result.verdict.ok, "host que falhou deveria dar FAIL")
        self.assertIn("claude_code falhou", result.verdict.reason)

    def test_host_real_timeout_e_ausente_viram_fail_limpo(self) -> None:
        """Timeout e binário ausente do subprocesso viram rc não-zero, não traceback."""
        import subprocess
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 1)):
            out = hosts.run_claude_code(Path("/tmp"), "oi", timeout_s=1)
        self.assertNotEqual(out["returncode"], 0)
        self.assertIn("timeout", out["stderr"])
        with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
            out = hosts.run_claude_code(Path("/tmp"), "oi")
        self.assertNotEqual(out["returncode"], 0)
        self.assertIn("não encontrado", out["stderr"])

    def test_apply_replay_recusa_path_fora_do_workspace(self) -> None:
        """Op de replay com path absoluto ou `..` não pode escapar do tmpdir."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            for bad in ("../fora.txt", "/tmp/absoluto.txt", "Prumo/../../fuga.txt"):
                with self.subTest(path=bad):
                    with self.assertRaises(ValueError):
                        hosts.apply_replay(ws, [{"op": "write", "path": bad, "content": "x"}])

    def test_oracle_inbox_exige_trilha_do_item(self) -> None:
        """Remoção com linha irrelevante no REGISTRO NÃO passa — a trilha tem de
        mencionar o item removido (o furo que o Codex apontou)."""
        c5 = scenarios.by_id("c5_inbox_removal")
        pos = next(c for c in c5.cases if c.variant == "pos")
        # A violation_ops do pos é exatamente 'remove + linha de fachada'.
        v = run.run_case_replay(c5, pos, "violation")
        self.assertFalse(v.verdict.ok)
        self.assertIn("não menciona o item", v.verdict.reason)


if __name__ == "__main__":
    unittest.main()
