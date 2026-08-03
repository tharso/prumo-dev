"""#311: o coletor de cobertura do quality gate.

Percentual medido sobre suite quebrada não é métrica — no caso real de
03/08, 3 módulos de teste falharam no load (ModuleNotFoundError), 34
testes sumiram e o gate reportou 83% como "regressão" quando a suite
íntegra media 87%. Cada ramo fail-closed travado com subprocess mockado,
no padrão do test_quality_gate_route.py.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "quality_gate", REPO_ROOT / "scripts" / "quality_gate.py"
)
_qg = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("quality_gate", _qg)
_spec.loader.exec_module(_qg)

TOTAL_87 = (
    "Name                Stmts   Miss  Cover\n"
    "---------------------------------------\n"
    "TOTAL                1000    130    87%\n"
)


def _proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class CollectCoverageTests(unittest.TestCase):
    def _run(self, procs: list[SimpleNamespace]) -> tuple[float, str, mock.MagicMock]:
        buf = io.StringIO()
        with mock.patch.object(_qg.subprocess, "run", side_effect=procs) as m:
            with contextlib.redirect_stdout(buf):
                result = _qg.collect_coverage()
        return result, buf.getvalue(), m

    def test_happy_path_returns_total(self) -> None:
        result, _, _ = self._run([_proc(), _proc(stdout=TOTAL_87)])
        self.assertEqual(result, 87.0)

    def test_suite_quebrada_fails_closed(self) -> None:
        stderr = (
            "Traceback (most recent call last):\n"
            "ModuleNotFoundError: No module named 'prumo_runtime'\n"
            "FAILED (errors=3)\n"
        )
        result, _, m = self._run([_proc(returncode=1, stderr=stderr)])
        self.assertEqual(result, -1.0)
        # Suite quebrada não tem o que medir: o coverage report nem roda.
        # (side_effect com um proc só — segunda chamada estouraria StopIteration)
        self.assertEqual(m.call_count, 1)

    def test_suite_quebrada_diagnostico_visivel(self) -> None:
        stderr = "ModuleNotFoundError: No module named 'prumo_runtime'"
        _, out, _ = self._run([_proc(returncode=1, stderr=stderr)])
        self.assertIn("suite quebrada", out)
        self.assertIn("ModuleNotFoundError", out)

    def test_report_sem_total_fails_closed(self) -> None:
        result, _, _ = self._run([_proc(), _proc(stdout="No data to report.\n")])
        self.assertEqual(result, -1.0)


class MainFailsClosedTests(unittest.TestCase):
    def test_main_para_sem_comparar_baseline(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(_qg, "collect_ruff_violations", return_value=0), \
                mock.patch.object(_qg, "collect_coverage", return_value=-1.0), \
                mock.patch.object(_qg, "collect_largest_file") as largest, \
                mock.patch.object(sys, "argv", ["quality_gate.py"]), \
                contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            rc = _qg.main()
        self.assertEqual(rc, 1)
        # O gate para na cobertura: nenhuma métrica seguinte é coletada
        # e o sentinela nunca chega ao check_metric como percentual.
        largest.assert_not_called()
        self.assertIn("não medida", stderr.getvalue())
        self.assertNotIn("coverage_pct", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
