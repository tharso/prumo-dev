"""Transporte de update pra instalação de diretório local (#170).

Bug: runtime instalado do cache do plugin (origem = diretório local, uv-tool
`copy`) recebia plano de registry (`uv tool install --force prumo-runtime`),
que falha — prumo-runtime não é publicado em registry. O plano tem que instalar
do PATH local da nova versão, resolvido do `uv-receipt.toml` (fonte agnóstica do
uv, não caminho de host). Sem path resolvível: erro honesto, não plano morto.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import io
import json
import os
import sys
import types
from contextlib import redirect_stdout
from unittest import mock

from prumo_runtime.commands.update import (
    build_update_plan,
    is_local_uv_install,
    resolve_local_source_dir,
    run_update,
    workspace_core_status,
)


def setUpModule():
    if sys.version_info < (3, 11):
        raise unittest.SkipTest(
            "prumo update requer tomllib (stdlib 3.11+); na mínima 3.10 o "
            "contrato do update é o gate de mensagem legível, provado em "
            "test_python_310_support (#301)"
        )


class BuildPlanCopyInstall(unittest.TestCase):
    def test_copy_install_usa_path_local_nao_registry(self) -> None:
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.16.0",
            remote_version="5.29.0",
            source_kind="copy",
            launcher="manual-uv-tool-copy",
            local_source_dir="/cache/prumo-marketplace/prumo/5.29.0",
            local_install=True,
        )
        self.assertTrue(plan["needs_update"])
        self.assertIn("/cache/prumo-marketplace/prumo/5.29.0", plan["command"])
        self.assertIn("uv tool install --force", plan["command"])
        # NÃO pode virar o alvo de registry.
        self.assertNotEqual(plan["command"].strip(), "uv tool install --force prumo-runtime")

    def test_copy_sem_path_local_cai_no_tarball(self) -> None:
        # #232 substitui o "erro honesto" da era #170: cache sem a versão
        # nova era o beco do caso real do dono — agora o plano cai no
        # transporte universal (tarball do espelho), mesmo instalador.
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.16.0",
            remote_version="5.29.0",
            source_kind="copy",
            launcher="manual-uv-tool-copy",
            local_source_dir=None,
            local_install=True,
        )
        self.assertTrue(plan["needs_update"])
        self.assertEqual(plan["command"], "archive")
        self.assertEqual(plan["archive_installer"], "uv")
        self.assertIn("espelho", plan["explanation"])

    def test_registry_nunca_mais(self) -> None:
        # #232: prumo-runtime NÃO é publicado — registry era beco hoje e
        # dependency confusion amanhã. uv "manual" também vai pro tarball.
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="archive",
            launcher="manual",
        )
        self.assertEqual(plan["command"], "archive")
        self.assertNotIn("prumo-runtime", plan.get("uv_target") or "")


class ResolveLocalSourceDir(unittest.TestCase):
    def _make_cache(self, root: Path, version: str, *, name: str = "prumo-runtime", pv: str | None = None) -> Path:
        d = root / "prumo-marketplace" / "prumo" / version
        d.mkdir(parents=True)
        (d / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "{pv or version}"\n', encoding="utf-8"
        )
        return d

    def _make_receipt(self, uv_tool_dir: Path, directory: Path) -> None:
        tool = uv_tool_dir / "prumo-runtime"
        tool.mkdir(parents=True)
        (tool / "uv-receipt.toml").write_text(
            "[tool]\n"
            f'requirements = [{{ name = "prumo-runtime", directory = "{directory}" }}]\n',
            encoding="utf-8",
        )

    def test_resolve_deriva_versao_nova_do_receipt(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cur = self._make_cache(root, "5.16.0")
            new = self._make_cache(root, "5.29.0")
            uv_dir = root / "uvtools"
            self._make_receipt(uv_dir, cur)
            got = resolve_local_source_dir("5.29.0", current_version="5.16.0", uv_tool_dir=uv_dir)
            self.assertEqual(Path(got), new)

    def test_resolve_none_quando_pasta_da_nova_versao_nao_existe(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cur = self._make_cache(root, "5.16.0")  # só a atual existe
            uv_dir = root / "uvtools"
            self._make_receipt(uv_dir, cur)
            got = resolve_local_source_dir("5.29.0", current_version="5.16.0", uv_tool_dir=uv_dir)
            self.assertIsNone(got)

    def test_resolve_valida_pyproject_nome_e_versao(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cur = self._make_cache(root, "5.16.0")
            # nova pasta existe, mas pyproject tem nome errado → inválida.
            self._make_cache(root, "5.29.0", name="outra-coisa")
            uv_dir = root / "uvtools"
            self._make_receipt(uv_dir, cur)
            got = resolve_local_source_dir("5.29.0", current_version="5.16.0", uv_tool_dir=uv_dir)
            self.assertIsNone(got)

    def test_resolve_none_sem_receipt(self) -> None:
        with TemporaryDirectory() as tmp:
            uv_dir = Path(tmp) / "uvtools"  # nem existe
            got = resolve_local_source_dir("5.29.0", current_version="5.16.0", uv_tool_dir=uv_dir)
            self.assertIsNone(got)


class WorkspaceCoreStatusReport(unittest.TestCase):
    def _ws(self, root: Path, version: str) -> Path:
        (root / ".prumo" / "system").mkdir(parents=True)
        (root / ".prumo" / "system" / "PRUMO-CORE.md").write_text(
            f"> **prumo_version: {version}**\n", encoding="utf-8"
        )
        return root

    def test_reporta_core_defasado(self) -> None:
        with TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp), "5.16.0")
            got = workspace_core_status(ws, "5.29.0")
            self.assertEqual(got["workspace_core_version"], "5.16.0")
            self.assertTrue(got["workspace_core_needs_update"])

    def test_core_em_dia_nao_pede_update(self) -> None:
        with TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp), "5.29.0")
            got = workspace_core_status(ws, "5.29.0")
            self.assertFalse(got["workspace_core_needs_update"])

    def test_none_fora_de_workspace(self) -> None:
        with TemporaryDirectory() as tmp:
            self.assertIsNone(workspace_core_status(Path(tmp), "5.29.0"))


class IsLocalUvInstall(unittest.TestCase):
    def _receipt(self, root: Path, directory: Path) -> Path:
        uvdir = root / "uvtools"
        (uvdir / "prumo-runtime").mkdir(parents=True)
        (uvdir / "prumo-runtime" / "uv-receipt.toml").write_text(
            "[tool]\n"
            f'requirements = [{{ name = "prumo-runtime", directory = "{directory}" }}]\n',
            encoding="utf-8",
        )
        return uvdir

    def test_copy_e_local(self) -> None:
        self.assertTrue(is_local_uv_install({"source_kind": "copy"}))

    def test_uv_tool_nao_install_script_com_receipt_e_local(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            uvdir = self._receipt(root, root / "prumo" / "5.16.0")
            mi = {"package_manager": "uv-tool", "launcher": "manual-uv-tool-copy", "source_kind": "archive"}
            self.assertTrue(is_local_uv_install(mi, uv_tool_dir=uvdir))

    def test_install_script_nao_e_local(self) -> None:
        # install-script tem transporte próprio (re-roda o script) e precedência.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            uvdir = self._receipt(root, root / "prumo" / "5.16.0")
            mi = {"package_manager": "uv-tool", "launcher": "install-script", "source_kind": "archive"}
            self.assertFalse(is_local_uv_install(mi, uv_tool_dir=uvdir))

    def test_editable_nao_e_local(self) -> None:
        mi = {"package_manager": "uv-tool", "launcher": "manual", "source_kind": "editable"}
        self.assertFalse(is_local_uv_install(mi))

    def test_uv_tool_sem_receipt_nao_e_local(self) -> None:
        with TemporaryDirectory() as tmp:
            uvdir = Path(tmp) / "uvtools"  # sem receipt
            mi = {"package_manager": "uv-tool", "launcher": "manual", "source_kind": "archive"}
            self.assertFalse(is_local_uv_install(mi, uv_tool_dir=uvdir))


class RunUpdateIntegration(unittest.TestCase):
    def test_run_update_descobre_origem_do_receipt_e_planeja_path_local(self) -> None:
        """End-to-end (#170): detect → is_local → resolve pelo receipt → plano
        com path local, sem tocar no registry."""
        from prumo_runtime import __version__

        cur, new = __version__, "5.99.0"
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "cache" / "prumo"
            (cache / cur).mkdir(parents=True)
            new_dir = cache / new
            new_dir.mkdir(parents=True)
            (new_dir / "pyproject.toml").write_text(
                f'[project]\nname = "prumo-runtime"\nversion = "{new}"\n', encoding="utf-8"
            )
            uvdir = root / "uvtools"
            (uvdir / "prumo-runtime").mkdir(parents=True)
            (uvdir / "prumo-runtime" / "uv-receipt.toml").write_text(
                "[tool]\n"
                f'requirements = [{{ name = "prumo-runtime", directory = "{cache / cur}" }}]\n',
                encoding="utf-8",
            )
            args = types.SimpleNamespace(check=True, dry_run=True, yes=False, format="json")
            method = {
                "launcher": "manual-uv-tool-copy", "package_manager": "uv-tool",
                "source_kind": "copy", "source": "marker", "is_editable": False, "details": {},
            }
            with mock.patch.dict(os.environ, {"UV_TOOL_DIR": str(uvdir)}), mock.patch(
                "prumo_runtime.commands.update.detect_install_method", return_value=method
            ), mock.patch(
                "prumo_runtime.commands.update.fetch_remote_version", return_value=new
            ):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    run_update(args)
                payload = json.loads(buf.getvalue())
            self.assertTrue(payload["needs_update"])
            self.assertIn(str(new_dir), payload["plan"]["command"])
            self.assertIn("uv tool install --force", payload["plan"]["command"])
            self.assertNotIn("--force prumo-runtime", payload["plan"]["command"])


if __name__ == "__main__":
    unittest.main()
