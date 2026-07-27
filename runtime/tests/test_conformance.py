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
        # A violation_ops do pos é exatamente 'move + linha de fachada'.
        v = run.run_case_replay(c5, pos, "violation")
        self.assertFalse(v.verdict.ok)
        self.assertIn("menção antiga não é trilha", v.verdict.reason)

    def test_c5_compliant_roda_em_host_sem_delecao(self) -> None:
        """O fluxo feliz do #242 não depende de deleção: as compliant_ops do pos
        rodam com `allow_delete=False` (a ponte do Cowork) e o oráculo PASSA."""
        import tempfile
        c5 = scenarios.by_id("c5_inbox_removal")
        pos = next(c for c in c5.cases if c.variant == "pos")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            run._setup_workspace(c5, ws)
            trace = hosts.apply_replay(ws, pos.compliant_ops, allow_delete=False)
            verdict = c5.oracle(ws, **{**pos.oracle_params, "trace": trace})
        self.assertTrue(verdict.ok, verdict.reason)

    def test_host_sem_delecao_bloqueia_delete(self) -> None:
        """`allow_delete=False` levanta PermissionError na op delete — o mesmo
        sintoma da ponte real do Cowork (Operation not permitted)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "x.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(PermissionError):
                hosts.apply_replay(ws, [{"op": "delete", "path": "x.txt"}], allow_delete=False)

    def test_c5_delete_recriacao_cai_pelo_trace(self) -> None:
        """Estado final idêntico ao move, mas o trace acusa a deleção — o caso
        que oráculo só-de-estado não pega (achado [P2-3] do Codex)."""
        c5 = scenarios.by_id("c5_inbox_removal")
        caso = next(c for c in c5.cases if c.variant == "pos_delete_recria")
        v = run.run_case_replay(c5, caso, "violation")
        self.assertFalse(v.verdict.ok)
        self.assertIn("DELEÇÃO", v.verdict.reason)

    def test_apply_replay_move_preserva_symlink(self) -> None:
        """Mover um symlink move o LINK, nunca o alvo (achado [P2-6])."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            alvo = ws / "alvo.txt"
            alvo.write_text("conteúdo do alvo", encoding="utf-8")
            link = ws / "link.txt"
            link.symlink_to(alvo)
            hosts.apply_replay(ws, [{"op": "move", "path": "link.txt", "dest": "q/link.txt"}])
            dest = ws / "q" / "link.txt"
            self.assertTrue(dest.is_symlink(), "destino deveria ser o próprio link")
            self.assertTrue(alvo.is_file(), "o alvo do link não pode ser tocado")
            self.assertFalse(link.is_symlink() or link.exists())

    def test_apply_replay_move_nunca_sobrescreve(self) -> None:
        """Destino de move já existente é erro — colisão nunca é silenciosa."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "a.txt").write_text("a", encoding="utf-8")
            (ws / "q").mkdir()
            (ws / "q" / "a.txt").write_text("já existe", encoding="utf-8")
            with self.assertRaises(ValueError):
                hosts.apply_replay(ws, [{"op": "move", "path": "a.txt", "dest": "q/a.txt"}])

    def test_c5_cobre_variantes_do_242(self) -> None:
        """As direções de segurança novas do #242 existem como casos pareados."""
        c5 = scenarios.by_id("c5_inbox_removal")
        variants = {c.variant for c in c5.cases}
        self.assertLessEqual(
            {"neg", "neg_copia", "neg_marcacao", "pos", "pos_delete_recria",
             "pos_sem_destino", "pos_sem_processed", "pos_move_destino_errado",
             "pos_delete_no_destino", "pos_colisao"},
            variants,
        )

    def test_oracle_positivo_reprova_symlink_pendurado_na_origem(self) -> None:
        """[D5]: link pendurado restante no inbox conta como PRESENTE — `exists()`
        puro diria 'removido' e o positivo passaria com lixo pra trás."""
        import tempfile
        from conformance.harness import oracles
        c5 = scenarios.by_id("c5_inbox_removal")
        pos = next(c for c in c5.cases if c.variant == "pos")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            run._setup_workspace(c5, ws)
            hosts.apply_replay(ws, pos.compliant_ops)
            item = ws / pos.oracle_params["item_rel"]
            item.symlink_to(ws / "alvo-que-nao-existe.txt")  # link pendurado
            verdict = c5.oracle(ws, **pos.oracle_params)
        self.assertFalse(verdict.ok)
        self.assertIn("symlink", verdict.reason)

    def test_oracle_destino_symlink_pendurado_da_fail_limpo(self) -> None:
        """[D5]: entrada ilegível na quarentena vira FAIL explícito, não traceback."""
        import tempfile
        from conformance.harness import oracles as _o
        c5 = scenarios.by_id("c5_inbox_removal")
        pos = next(c for c in c5.cases if c.variant == "pos")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            run._setup_workspace(c5, ws)
            # Remoção "completa" mas o destino é um link pendurado com o nome certo.
            hosts.apply_replay(ws, [op for op in pos.compliant_ops if op["op"] != "move"])
            (ws / pos.oracle_params["item_rel"]).unlink()
            qdir = ws / _o.QUARANTINE_DIR / "2026-03-20_inbox"
            qdir.mkdir(parents=True)
            (qdir / "captura-exemplo.txt").symlink_to(ws / "sumiu.txt")
            verdict = c5.oracle(ws, **pos.oracle_params)
        self.assertFalse(verdict.ok)
        self.assertIn("ilegível", verdict.reason)

    def test_safe_parent_recusa_pai_symlink_pra_fora(self) -> None:
        """[D6]: origem OU destino cujo pai é symlink pra fora do workspace →
        ValueError antes de qualquer efeito (inclusive com subpasta inexistente)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as fora:
            ws = Path(tmp)
            (ws / "escape").symlink_to(Path(fora))
            (ws / "a.txt").write_text("a", encoding="utf-8")
            with self.assertRaises(ValueError):
                hosts.apply_replay(
                    ws, [{"op": "move", "path": "a.txt", "dest": "escape/a.txt"}]
                )
            with self.assertRaises(ValueError):
                hosts.apply_replay(
                    ws, [{"op": "move", "path": "a.txt", "dest": "escape/sub-nova/a.txt"}]
                )
            (Path(fora) / "b.txt").write_text("b", encoding="utf-8")
            with self.assertRaises(ValueError):
                hosts.apply_replay(
                    ws, [{"op": "move", "path": "escape/b.txt", "dest": "q/b.txt"}]
                )
            self.assertTrue((Path(fora) / "b.txt").is_file(), "efeito vazou pra fora do ws")

    def test_safe_parent_aceita_pai_symlink_interno(self) -> None:
        """[D6]: pai symlink que resolve DENTRO do workspace é permitido —
        comportamento documentado, não brecha."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "real").mkdir()
            (ws / "alias").symlink_to(ws / "real")
            (ws / "a.txt").write_text("a", encoding="utf-8")
            hosts.apply_replay(ws, [{"op": "move", "path": "a.txt", "dest": "alias/a.txt"}])
            self.assertTrue((ws / "real" / "a.txt").is_file())


if __name__ == "__main__":
    unittest.main()
