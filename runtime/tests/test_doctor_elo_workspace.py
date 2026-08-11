"""#335 (C-lite) — o elo do workspace no `prumo doctor --host`.

A #324 nomeou o clone congelado da store; este elo nomeia o vizinho: o
checkout embarcado do workspace defasado em relação ao runtime QUE EXECUTA o
diagnóstico (cobre a invocação `PYTHONPATH=<bundle>`). Contratos: quatro
estados fechados (`sem workspace` / `legacy_flat` / `core em
em_dia|divergente|indeterminado`), direção preservada, e coerência régua ×
fonte — o doctor só prescreve `recommended_command` quando o `prumo` do PATH
coincide em versão com o runtime em execução; o ACHADO sai sempre.

Elo local: todos os testes rodam com a rede mockada em None (sem rede).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from prumo_runtime import __version__
from prumo_runtime.commands import doctor


def _args(**kw):
    base = {"host": True, "format": "json", "network_timeout": 0.1}
    base.update(kw)
    return argparse.Namespace(**base)


def _nested(root: Path, core_line: str | None) -> Path:
    (root / ".prumo" / "system").mkdir(parents=True)
    if core_line is not None:
        (root / ".prumo" / "system" / "PRUMO-CORE.md").write_text(
            core_line, encoding="utf-8"
        )
    return root


def _flat(root: Path) -> Path:
    (root / "_state").mkdir()
    (root / "_state" / "workspace-schema.json").write_text("{}", encoding="utf-8")
    (root / "PRUMO-CORE.md").write_text("> **prumo_version: 5.0.0**\n", encoding="utf-8")
    return root


_FORBIDDEN = object()


class _Base(unittest.TestCase):
    def _run(self, cwd: Path, *, fmt: str = "json",
             which: str | None = "/usr/local/bin/prumo", probe=_FORBIDDEN):
        """Roda o doctor com rede None, store ausente e CWD controlado.

        `which`: retorno de shutil.which (o campo `runtime_on_path` também o
        consome, então ele roda em qualquer ramo — o custo vigiado é outro).
        `probe`: resultado de `prumo --version`. Default: PROIBIDO — todo
        ramo que não prescreve comando prova de graça que nenhum subprocesso
        roda (em_dia/indeterminado/sem workspace não pagam sonda).
        """
        stdout = io.StringIO()
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(doctor, "_fetch_remote", return_value=None))
        stack.enter_context(
            mock.patch.object(doctor, "_collect_store", return_value={"found": False, "status": "ausente"})
        )
        stack.enter_context(mock.patch.object(doctor.Path, "cwd", return_value=cwd))
        stack.enter_context(mock.patch.object(doctor.shutil, "which", return_value=which))
        if probe is _FORBIDDEN:
            kwargs = {"side_effect": AssertionError("sonda do PATH não pode rodar neste ramo")}
        elif isinstance(probe, Exception):
            kwargs = {"side_effect": probe}
        else:
            kwargs = {"return_value": probe}
        stack.enter_context(mock.patch.object(doctor.subprocess, "run", **kwargs))
        with stack:
            with contextlib.redirect_stdout(stdout):
                rc = doctor.run_doctor(_args(format=fmt))
        self.assertEqual(rc, 0)
        out = stdout.getvalue()
        return (json.loads(out) if fmt == "json" else out)

    def _probe_ok(self):
        return mock.MagicMock(returncode=0, stdout=f"prumo {__version__}\n")


class ForaDeWorkspaceTests(_Base):
    def test_bloco_explicito_no_json_e_linha_no_texto(self):
        """Ausência nunca é silêncio — fora de workspace o bloco existe e diz."""
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run(Path(tmp))
            self.assertEqual(payload["schema"], "prumo_doctor_host.v1")
            self.assertEqual(payload["workspace"], {"detected": False})
        with tempfile.TemporaryDirectory() as tmp:
            texto = self._run(Path(tmp), fmt="text")
            self.assertIn("workspace", texto)
            self.assertIn("nenhum", texto)


class NestedTests(_Base):
    def test_em_dia_por_igualdade_real_sem_sonda(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), f"> **prumo_version: {__version__}**\n")
            payload = self._run(ws)
            core = payload["workspace"]["core"]
            self.assertEqual(core["status"], "em_dia")
            self.assertEqual(core["version"], __version__)
            self.assertNotIn("direction", core)

    def test_core_atras_divergente_com_direcao_e_comando(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 0.1.0**\n")
            payload = self._run(ws, which="/usr/local/bin/prumo", probe=self._probe_ok())
            core = payload["workspace"]["core"]
            self.assertEqual(core["status"], "divergente")
            self.assertEqual(core["direction"], "core_behind_runtime")
            self.assertEqual(core["version"], "0.1.0")
            self.assertEqual(core["runtime_version"], __version__)
            self.assertEqual(core["recommended_command"], "prumo repair --workspace .")
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 0.1.0**\n")
            texto = self._run(ws, fmt="text", which="/usr/local/bin/prumo", probe=self._probe_ok())
            self.assertIn("DEFASADO", texto)
            self.assertIn("prumo repair --workspace .", texto)

    def test_core_a_frente_nunca_vira_em_dia(self):
        """Direção preservada: core mais novo que o runtime em execução é
        divergência (runtime velho ou core adulterado), jamais saúde."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 99.0.0**\n")
            payload = self._run(ws, which="/usr/local/bin/prumo", probe=self._probe_ok())
            core = payload["workspace"]["core"]
            self.assertEqual(core["status"], "divergente")
            self.assertEqual(core["direction"], "core_ahead_of_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 99.0.0**\n")
            texto = self._run(ws, fmt="text", which="/usr/local/bin/prumo", probe=self._probe_ok())
            self.assertIn("velho", texto)  # hipótese de runtime velho, declarada

    def test_core_malformado_e_indeterminado_nunca_direcao_inventada(self):
        casos = [
            "> **prumo_version: abc**\n",   # não parseável como tupla numérica
            "sem linha de versao\n",         # linha ausente → parse devolve None
        ]
        for core_line in casos:
            with tempfile.TemporaryDirectory() as tmp:
                ws = _nested(Path(tmp), core_line)
                payload = self._run(ws)
                core = payload["workspace"]["core"]
                self.assertEqual(core["status"], "indeterminado", core_line)
                self.assertNotIn("direction", core, core_line)
                self.assertNotIn("recommended_command", core, core_line)


class FlatTests(_Base):
    def test_flat_tem_precedencia_e_nunca_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat(Path(tmp))
            payload = self._run(ws, which="/usr/local/bin/prumo", probe=self._probe_ok())
            bloco = payload["workspace"]
            self.assertEqual(bloco["layout"], "flat")
            self.assertEqual(bloco["status"], "legacy_flat")
            self.assertNotIn("core", bloco)  # a comparação não ocorre no flat
            self.assertEqual(bloco["recommended_command"], "prumo migrate --workspace .")
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat(Path(tmp))
            texto = self._run(ws, fmt="text", which="/usr/local/bin/prumo", probe=self._probe_ok())
            self.assertIn("migrate", texto)
            self.assertNotIn("prumo repair", texto)


class CoerenciaReguaFonteTests(_Base):
    """Delta 5: o comando só sai quando quem o executaria (PATH) coincide com
    a régua (runtime em execução). O achado sai SEMPRE."""

    def test_path_divergente_reporta_mas_nao_prescreve(self):
        probe = mock.MagicMock(returncode=0, stdout="prumo 0.9.9\n")
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 0.1.0**\n")
            payload = self._run(ws, which="/x/prumo", probe=probe)
            core = payload["workspace"]["core"]
            self.assertEqual(core["status"], "divergente")     # achado preservado
            self.assertIsNone(core["recommended_command"])      # prescrição suprimida
            self.assertEqual(core["path_runtime_version"], "0.9.9")
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 0.1.0**\n")
            texto = self._run(ws, fmt="text", which="/x/prumo", probe=probe)
            self.assertIn("PATH", texto)
            self.assertIn("0.9.9", texto)
            self.assertNotIn("prumo repair --workspace .", texto)

    def test_path_ausente_reporta_e_aponta_passo_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 0.1.0**\n")
            payload = self._run(ws, which=None)
            core = payload["workspace"]["core"]
            self.assertEqual(core["status"], "divergente")
            self.assertIsNone(core["recommended_command"])
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 0.1.0**\n")
            texto = self._run(ws, fmt="text", which=None)
            self.assertIn("passo 0", texto)
            self.assertNotIn("prumo repair --workspace .", texto)

    def test_sonda_falhando_nunca_prescreve_fonte_nao_verificada(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested(Path(tmp), "> **prumo_version: 0.1.0**\n")
            payload = self._run(
                ws, which="/x/prumo", probe=doctor.subprocess.SubprocessError("timeout")
            )
            core = payload["workspace"]["core"]
            self.assertEqual(core["status"], "divergente")
            self.assertIsNone(core["recommended_command"])
            self.assertIsNone(core["path_runtime_version"])


if __name__ == "__main__":
    unittest.main()
