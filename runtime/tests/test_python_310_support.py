"""Suporte a Python 3.10 — decisão de 2026-08-03 (#301).

O runtime declara `requires-python >= 3.10` porque o host oficial do Cowork
(VM Ubuntu 22.04) fornece Python 3.10. O único uso de stdlib 3.11+ é o
`tomllib` do comando update, atrás de import adiado + gate com mensagem
legível. Estes testes travam o contrato nas duas pontas — o código que não
pode regredir e o CI que precisa exercitar a mínima — porque CI verde só em
3.11 não diz nada sobre o host real: foi esse o ponto cego que escondeu o
runtime do Cowork por nove dias.
"""

import argparse
import ast
import contextlib
import importlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "runtime" / "prumo_runtime"


class _TomllibBlocker:
    """Meta path finder que simula um interpretador sem tomllib (3.10)."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "tomllib":
            raise ModuleNotFoundError("No module named 'tomllib' (simulado por teste)")
        return None


class TestCliImportsWithoutTomllib(unittest.TestCase):
    def test_cli_and_all_commands_import_without_tomllib(self):
        """A cadeia __main__ → cli → commands/* precisa carregar sem tomllib.

        É a reprodução fiel do incidente: em 3.10 real não existe tomllib e
        TODO comando morria na carga, inclusive briefing/seed/start/repair.
        """
        saved = {
            name: mod
            for name, mod in list(sys.modules.items())
            if name == "tomllib" or name.split(".")[0] == "prumo_runtime"
        }
        for name in saved:
            del sys.modules[name]
        blocker = _TomllibBlocker()
        sys.meta_path.insert(0, blocker)
        try:
            cli = importlib.import_module("prumo_runtime.cli")
            self.assertTrue(callable(cli.main))
        finally:
            sys.meta_path.remove(blocker)
            for name in [n for n in sys.modules if n.split(".")[0] == "prumo_runtime"]:
                del sys.modules[name]
            sys.modules.update(saved)


class TestNoEagerTomllibImport(unittest.TestCase):
    def test_no_module_level_tomllib_import_in_package(self):
        """Anti-regressão do ponto cego exato: um único import ansioso num
        módulo alcançável por commands/__init__ derruba o CLI inteiro na
        mínima suportada. tomllib só pode aparecer dentro de função."""
        offenders = []
        for py in sorted(PACKAGE_ROOT.rglob("*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.Import):
                    if any(
                        alias.name == "tomllib" or alias.name.startswith("tomllib.")
                        for alias in node.names
                    ):
                        offenders.append(str(py.relative_to(REPO_ROOT)))
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[0] == "tomllib":
                        offenders.append(str(py.relative_to(REPO_ROOT)))
        self.assertEqual(
            offenders,
            [],
            "import tomllib no nível de módulo derruba todos os comandos em "
            f"Python 3.10 (#301). Mover pra dentro da função: {offenders}",
        )


class TestRequirePython(unittest.TestCase):
    def test_below_minimum_aborts_with_readable_message(self):
        import prumo_runtime

        with self.assertRaises(SystemExit) as ctx:
            prumo_runtime._require_python((3, 9))
        message = str(ctx.exception.code)
        self.assertIn("3.10", message)
        self.assertIn("3.9", message)

    def test_minimum_and_above_pass(self):
        import prumo_runtime

        prumo_runtime._require_python((3, 10))
        prumo_runtime._require_python((3, 12))


class TestUpdateGateBelow311(unittest.TestCase):
    def test_predicate_reads_version(self):
        from prumo_runtime.commands import update

        self.assertFalse(update._python_supports_update((3, 10, 12)))
        self.assertTrue(update._python_supports_update((3, 11, 0)))

    def test_run_update_refuses_below_311_with_readable_message(self):
        """Em 3.10 o update degrada com mensagem, nunca com traceback — e os
        demais comandos não passam por este gate."""
        from prumo_runtime.commands import update

        stderr = io.StringIO()
        with mock.patch.object(update, "_python_supports_update", return_value=False):
            with contextlib.redirect_stderr(stderr):
                rc = update.run_update(argparse.Namespace())
        self.assertEqual(rc, 2)
        message = stderr.getvalue()
        self.assertIn("3.11", message)
        self.assertIn("update", message)


class TestInstallersAcceptMinimum(unittest.TestCase):
    """O instalador oficial acompanha o contrato (achado do Codex, PR #310 r1):
    com a mínima em 3.10, nenhum caminho de instalação pode exigir 3.11 — nem
    pin de `--python 3.11` no uv (o requires-python do pyproject é a fonte),
    nem loop de candidatos sem `python3.10`."""

    def test_shell_installers_accept_310(self):
        for name in ("prumo_runtime_install.sh", "prumo_runtime_update.sh"):
            text = (REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("python3.10", text, name)
            self.assertNotIn("--python 3.11", text, name)

    def test_powershell_installers_accept_310(self):
        for name in ("prumo_runtime_install.ps1", "prumo_runtime_update.ps1"):
            text = (REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("3.10", text, name)
            self.assertNotIn("--python 3.11", text, name)


class TestContractDeclaredAndExercised(unittest.TestCase):
    """O par que não pode se separar: a mínima declarada e o CI que a exercita.

    Mutações que este guard mata: subir requires-python de volta sem decisão;
    remover o job 3.10 deixando a declaração sem guarda (suporte acidental)."""

    def test_pyproject_declares_minimum_310(self):
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('requires-python = ">=3.10"', text)

    def test_ci_exercises_declared_minimum(self):
        text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn('python-version: "3.10"', text)


if __name__ == "__main__":
    unittest.main()
