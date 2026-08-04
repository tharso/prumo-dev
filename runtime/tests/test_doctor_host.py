"""`prumo doctor --host` (#309): o diagnóstico do host numa chamada.

O achado do tomllib custou ~7 chamadas de investigação na unha (relatório de
campo de 03/08, §8.3); com isto custa uma. O modo `--host` é explícito, não
default: deixa espaço pros diagnósticos da #299 (bundle × `.prumo/skills`)
entrarem no mesmo comando sem quebrar contrato. Rodar o comando JÁ É a prova
de executabilidade do runtime neste interpretador — inclusive do embarcado,
quando invocado com `PYTHONPATH=<bundle> python3 -m prumo_runtime`.
"""

import argparse
import contextlib
import io
import json
import sys
import unittest
from unittest import mock

from prumo_runtime import MINIMUM_PYTHON, __version__
from prumo_runtime.cli import build_parser
from prumo_runtime.commands import doctor


def _args(**kw):
    base = {"host": True, "format": "text", "network_timeout": 0.1}
    base.update(kw)
    return argparse.Namespace(**base)


class TestDoctorHostPayload(unittest.TestCase):
    def test_json_payload_carrega_os_fatos_do_host(self):
        stdout = io.StringIO()
        # #324: a sonda virou fetch do VERSION remoto (uma ida só, com cb);
        # a store é injetada pra não tocar a $HOME real do runner.
        with mock.patch.object(doctor, "_fetch_remote", return_value="9.9.9"):
            with mock.patch.object(
                doctor, "_collect_store", return_value={"found": False, "status": "ausente"}
            ):
                with contextlib.redirect_stdout(stdout):
                    rc = doctor.run_doctor(_args(format="json"))
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["schema"], "prumo_doctor_host.v1")
        self.assertEqual(payload["runtime_version"], __version__)
        self.assertEqual(
            payload["python"],
            f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
        )
        self.assertEqual(
            payload["minimum_python"], f"{MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}"
        )
        self.assertTrue(payload["python_ok"])
        self.assertTrue(payload["executable_here"])
        self.assertEqual(payload["network"], "ok")
        self.assertIn("runtime_on_path", payload)
        self.assertIn("os", payload)

    def test_texto_diz_o_essencial(self):
        stdout = io.StringIO()
        with mock.patch.object(doctor, "_fetch_remote", return_value=None):
            with mock.patch.object(
                doctor, "_collect_store", return_value={"found": False, "status": "ausente"}
            ):
                with contextlib.redirect_stdout(stdout):
                    rc = doctor.run_doctor(_args())
        self.assertEqual(rc, 0)
        texto = stdout.getvalue()
        self.assertIn(f"{sys.version_info[0]}.{sys.version_info[1]}", texto)
        self.assertIn("rede", texto.lower())
        self.assertIn("bloqueada", texto.lower())
        self.assertIn(__version__, texto)

    def test_rede_bloqueada_nao_derruba_o_diagnostico(self):
        """No host que motivou o comando (VM do Cowork) a rede é bloqueada —
        a sonda degrada, nunca traceback. Desde a #324 a sonda é o
        `fetch_remote_version` do update: aqui o urlopen REAL do módulo do
        update levanta URLError e o doctor atravessa inteiro — rede
        'blocked', remoto None, rc 0."""
        import urllib.error

        from prumo_runtime.commands import update as update_module

        stdout = io.StringIO()
        with mock.patch.object(
            update_module.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("tunnel 403"),
        ):
            with mock.patch.object(
                doctor, "_collect_store", return_value={"found": False, "status": "ausente"}
            ):
                with contextlib.redirect_stdout(stdout):
                    rc = doctor.run_doctor(_args(format="json"))
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["network"], "blocked")
        self.assertIsNone(payload["remote_version"])


class TestDoctorWiring(unittest.TestCase):
    def test_parser_aceita_doctor_host(self):
        args = build_parser().parse_args(["doctor", "--host"])
        self.assertIs(args.handler, doctor.run_doctor)
        self.assertTrue(args.host)

    def test_doctor_sem_host_explica(self):
        """Sem modo, erro de uso apontando --host — não um diagnóstico vazio."""
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                build_parser().parse_args(["doctor"])
        self.assertNotEqual(ctx.exception.code, 0)
        self.assertIn("--host", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
