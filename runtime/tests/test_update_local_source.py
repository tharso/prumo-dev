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

from prumo_runtime.commands.update import (
    build_update_plan,
    resolve_local_source_dir,
    workspace_core_status,
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
        )
        self.assertTrue(plan["needs_update"])
        self.assertIn("/cache/prumo-marketplace/prumo/5.29.0", plan["command"])
        self.assertIn("uv tool install --force", plan["command"])
        # NÃO pode virar o alvo de registry.
        self.assertNotEqual(plan["command"].strip(), "uv tool install --force prumo-runtime")

    def test_copy_sem_path_local_e_erro_honesto(self) -> None:
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.16.0",
            remote_version="5.29.0",
            source_kind="copy",
            launcher="manual-uv-tool-copy",
            local_source_dir=None,
        )
        self.assertTrue(plan["needs_update"])
        # Erro honesto: sem comando executável, explicação clara (não um plano que morre).
        self.assertIsNone(plan["command"])
        self.assertIn("local", plan["explanation"].lower())
        self.assertNotIn("prumo-runtime", plan["explanation"] or "")

    def test_registry_continua_indo_pro_registry(self) -> None:
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="archive",
            launcher="manual",
        )
        self.assertEqual(plan["command"], "uv tool install --force prumo-runtime")


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


if __name__ == "__main__":
    unittest.main()
