"""#180 PR11b: o coletor da métrica `briefing_f0f1_words` no quality gate.

Cada ramo fail-closed travado com subprocess mockado — o gate nunca pode
aprovar com o termômetro quebrado (rc≠0, JSON inválido, errors[] do audit,
campo do pior perfil ausente).
"""
from __future__ import annotations

import importlib.util
import json
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


def _proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class CollectBriefingRouteWorstTests(unittest.TestCase):
    def _run(self, proc: SimpleNamespace) -> int:
        with mock.patch.object(_qg.subprocess, "run", return_value=proc):
            return _qg.collect_briefing_route_worst()

    def test_happy_path_returns_worst_total(self) -> None:
        payload = {"errors": [], "worst_profile_total": 6788}
        self.assertEqual(self._run(_proc(stdout=json.dumps(payload))), 6788)

    def test_nonzero_rc_fails_closed(self) -> None:
        self.assertEqual(self._run(_proc(returncode=2, stderr="boom")), -1)

    def test_invalid_json_fails_closed(self) -> None:
        self.assertEqual(self._run(_proc(stdout="{nem json")), -1)

    def test_audit_errors_fail_closed(self) -> None:
        payload = {"errors": ["AGENTS.md ausente"], "worst_profile_total": 6788}
        self.assertEqual(self._run(_proc(stdout=json.dumps(payload))), -1)

    def test_missing_worst_field_fails_closed(self) -> None:
        payload = {"errors": [], "worst_profile_total": None}
        self.assertEqual(self._run(_proc(stdout=json.dumps(payload))), -1)


if __name__ == "__main__":
    unittest.main()
