"""
Testes do comando `prumo update` (#86).

Cobre: marker granular (schema v1.0), detecção via importlib.metadata,
confirmação interativa (--yes / TTY), curl seguro via temp file,
pós-update feedback, workspace detection, alias `prumo upgrade`,
modos --check/--dry-run.

Update real **não roda em CI** — todos os testes mockam _execute_plan.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from prumo_runtime import __version__
from prumo_runtime.cli import main
from prumo_runtime.commands.update import (
    build_update_plan,
    detect_install_method,
    install_marker_path,
)


def _write_marker_v1(path: Path, **overrides) -> None:
    """Grava marker no schema granular v1.0."""
    marker = {
        "schema_version": "1.0",
        "installed_version": "5.3.0",
        "installed_at": "2026-05-05T20:00:00Z",
        "launcher": "install-script",
        "package_manager": "uv-tool",
        "source_kind": "archive",
        "source": "https://github.com/tharso/prumo/archive/refs/heads/main.tar.gz",
        "python": "/usr/bin/python3.11",
        "prumo_executable": "/home/user/.local/bin/prumo",
    }
    marker.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marker), encoding="utf-8")


def _write_legacy_marker(path: Path, method: str) -> None:
    """Grava marker no formato antigo (pre-refactor) pra testar compat."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"method": method, "source": "https://example", "installed_at": "2026-05-05T20:00:00Z"}),
        encoding="utf-8",
    )


class DetectInstallMethodTests(unittest.TestCase):
    """Detecção de método de instalação via marker granular ou fallback."""

    def test_reads_granular_marker_uv_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="uv-tool")
            result = detect_install_method(marker)
            self.assertEqual(result["package_manager"], "uv-tool")
            self.assertEqual(result["launcher"], "install-script")
            self.assertEqual(result["source"], "marker")
            self.assertEqual(result["source_kind"], "archive")

    def test_reads_granular_marker_pip_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user")
            result = detect_install_method(marker)
            self.assertEqual(result["package_manager"], "pip-user")
            self.assertEqual(result["source"], "marker")

    def test_reads_legacy_marker_curl_as_install_script(self) -> None:
        """Marker no formato antigo {"method": "curl"} ainda é legível."""
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_legacy_marker(marker, "curl")
            result = detect_install_method(marker)
            self.assertEqual(result["launcher"], "install-script")
            self.assertEqual(result["package_manager"], "unknown")
            self.assertEqual(result["source"], "marker")

    def test_reads_legacy_marker_pip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_legacy_marker(marker, "pip")
            result = detect_install_method(marker)
            self.assertEqual(result["launcher"], "manual")
            self.assertEqual(result["package_manager"], "pip-user")
            self.assertEqual(result["source"], "marker")

    def test_legacy_marker_pip_emits_warning(self) -> None:
        """Marker legado pip deve ter warning de baixa confiança."""
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_legacy_marker(marker, "pip")
            result = detect_install_method(marker)
            self.assertIn("warning", result)
            self.assertIn("legado", result["warning"].lower())

    def test_corrupt_marker_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            marker.write_text("not json {", encoding="utf-8")
            with patch("prumo_runtime.commands.update.importlib.metadata.version", side_effect=Exception):
                result = detect_install_method(marker)
            self.assertEqual(result["source"], "fallback")

    def test_no_marker_uses_importlib_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            absent_marker = Path(tmpdir) / "install-method.json"
            with patch(
                "prumo_runtime.commands.update.importlib.metadata.version",
                return_value="5.3.0",
            ):
                result = detect_install_method(absent_marker)
            self.assertEqual(result["package_manager"], "pip-user")
            self.assertEqual(result["source"], "fallback")
            self.assertIn("importlib", result["details"]["reason"])

    def test_no_marker_no_importlib_returns_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            absent_marker = Path(tmpdir) / "install-method.json"
            with patch(
                "prumo_runtime.commands.update.importlib.metadata.version",
                side_effect=Exception("not found"),
            ):
                result = detect_install_method(absent_marker)
            self.assertEqual(result["package_manager"], "unknown")
            self.assertEqual(result["source"], "fallback")

    def test_editable_install_detected_via_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, source_kind="editable")
            result = detect_install_method(marker)
            self.assertEqual(result["source_kind"], "editable")
            self.assertTrue(result["is_editable"])

    def test_install_marker_path_is_xdg_compliant_on_unix(self) -> None:
        with patch.dict("os.environ", {"XDG_DATA_HOME": "/tmp/xdg-test"}, clear=False):
            with patch("prumo_runtime.commands.update.sys.platform", "linux"):
                path = install_marker_path()
                self.assertEqual(
                    path,
                    Path("/tmp/xdg-test") / "prumo" / "install-method.json",
                )

    def test_python_mismatch_warning(self) -> None:
        """Se sys.executable diverge do python no marker, retorna warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, python="/usr/bin/python3.11")
            with patch("prumo_runtime.commands.update.sys.executable", "/other/python3.12"):
                result = detect_install_method(marker)
            self.assertIn("warning", result)
            self.assertIn("python", result["warning"].lower())


class BuildUpdatePlanTests(unittest.TestCase):
    """Geração de plano de update baseado no método detectado."""

    def test_pip_user_manual_uses_archive_transport(self) -> None:
        """#232: pip-user NUNCA vai pro registry (prumo-runtime não é
        publicado — seria dependency confusion) — tarball do espelho,
        preservando o gerenciador."""
        plan = build_update_plan(
            package_manager="pip-user",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="archive",
            launcher="manual",
        )
        self.assertTrue(plan["needs_update"])
        self.assertEqual(plan["command"], "archive")
        self.assertEqual(plan["archive_installer"], "pip-user")
        self.assertIn("espelho", plan["explanation"])

    def test_uv_tool_manual_uses_archive_transport(self) -> None:
        """#232: uv-tool sem diretório local também vai pro tarball."""
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="archive",
            launcher="manual",
        )
        self.assertTrue(plan["needs_update"])
        self.assertEqual(plan["command"], "archive")
        self.assertEqual(plan["archive_installer"], "uv")

    def test_install_script_launcher_returns_script_rerun(self) -> None:
        plan = build_update_plan(
            package_manager="unknown",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="archive",
            launcher="install-script",
        )
        self.assertTrue(plan["needs_update"])
        self.assertIn("install", plan["command"].lower())

    def test_install_script_takes_priority_over_package_manager(self) -> None:
        """launcher=install-script sempre re-executa script, mesmo com uv-tool."""
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="archive",
            launcher="install-script",
        )
        self.assertTrue(plan["needs_update"])
        self.assertEqual(plan["command"], "install-script")
        self.assertIn("main", plan["explanation"])

    def test_no_update_needed_when_versions_match(self) -> None:
        plan = build_update_plan(
            package_manager="pip-user",
            current_version="5.3.0",
            remote_version="5.3.0",
            source_kind="archive",
        )
        self.assertFalse(plan["needs_update"])
        self.assertIsNone(plan["command"])

    def test_remote_version_none_means_offline(self) -> None:
        plan = build_update_plan(
            package_manager="pip-user",
            current_version="5.3.0",
            remote_version=None,
            source_kind="archive",
        )
        self.assertFalse(plan["needs_update"])
        self.assertIsNone(plan["command"])
        self.assertIn("offline", plan["explanation"].lower())

    def test_unknown_method_reruns_install_script(self) -> None:
        # #232 (emenda do Codex): unknown → install-script, que resolve
        # uv/Python e grava o marker — nunca pip improvisado de registry.
        plan = build_update_plan(
            package_manager="unknown",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="unknown",
        )
        self.assertTrue(plan["needs_update"])
        self.assertEqual(plan["command"], "install-script")
        self.assertIn("estado conhecido", plan["explanation"])

    def test_editable_install_blocks_auto_update(self) -> None:
        plan = build_update_plan(
            package_manager="pip-user",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="editable",
        )
        self.assertTrue(plan["needs_update"])
        self.assertIsNone(plan["command"])
        self.assertIn("editable", plan["explanation"].lower())
        self.assertIn("git pull", plan["explanation"].lower())

    def test_local_version_greater_than_remote_no_downgrade(self) -> None:
        plan = build_update_plan(
            package_manager="pip-user",
            current_version="5.4.0",
            remote_version="5.3.0",
            source_kind="archive",
        )
        self.assertFalse(plan["needs_update"])
        self.assertIn("local", plan["explanation"].lower())


class ConfirmationTests(unittest.TestCase):
    """Testa prompt de confirmação e --yes."""

    def _run_main_capturing(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_yes_flag_skips_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=(0, "5.99.0"),
            ) as mock_exec, patch(
                "prumo_runtime.commands.update._confirm_update",
                return_value=True,
            ) as mock_confirm:
                rc, _ = self._run_main_capturing(["update", "--yes"])
            mock_confirm.assert_not_called()
            mock_exec.assert_called_once()

    def test_no_yes_calls_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=(0, "5.99.0"),
            ), patch(
                "prumo_runtime.commands.update._confirm_update",
                return_value=True,
            ) as mock_confirm:
                rc, _ = self._run_main_capturing(["update"])
            mock_confirm.assert_called_once()

    def test_confirm_rejected_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=(0, "5.99.0"),
            ) as mock_exec, patch(
                "prumo_runtime.commands.update._confirm_update",
                return_value=False,
            ):
                rc, output = self._run_main_capturing(["update"])
            mock_exec.assert_not_called()
            self.assertEqual(rc, 2)

    def test_non_tty_without_yes_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=(0, "5.99.0"),
            ) as mock_exec, patch(
                "prumo_runtime.commands.update.sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = False
                rc, output = self._run_main_capturing(["update"])
            mock_exec.assert_not_called()
            self.assertEqual(rc, 2)


class PostUpdateTests(unittest.TestCase):
    """Testa feedback pós-update e sugestão de repair."""

    def _run_main_capturing(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_post_update_reports_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=(0, "5.99.0"),
            ), patch(
                "prumo_runtime.commands.update._confirm_update",
                return_value=True,
            ), patch(
                "prumo_runtime.commands.update._get_post_update_version",
                return_value="5.99.0",
            ):
                rc, output = self._run_main_capturing(["update", "--yes", "--format", "json"])
            payload = json.loads(output)
            self.assertEqual(payload["post_update"]["new_version"], "5.99.0")

    def test_post_update_version_failure_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=(0, "5.99.0"),
            ), patch(
                "prumo_runtime.commands.update._confirm_update",
                return_value=True,
            ), patch(
                "prumo_runtime.commands.update._get_post_update_version",
                return_value=None,
            ):
                rc, output = self._run_main_capturing(["update", "--yes", "--format", "json"])
            payload = json.loads(output)
            self.assertEqual(rc, 0)
            self.assertIsNone(payload["post_update"]["new_version"])

    def test_workspace_detected_suggests_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            # Cria .prumo/ no CWD pra simular workspace
            prumo_dir = Path(tmpdir) / ".prumo"
            prumo_dir.mkdir()
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=(0, "5.99.0"),
            ), patch(
                "prumo_runtime.commands.update._confirm_update",
                return_value=True,
            ), patch(
                "prumo_runtime.commands.update._get_post_update_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update.Path.cwd",
                return_value=Path(tmpdir),
            ):
                rc, output = self._run_main_capturing(["update", "--yes", "--format", "json"])
            payload = json.loads(output)
            self.assertTrue(payload["post_update"]["workspace_detected"])
            self.assertTrue(payload["post_update"]["repair_suggested"])

    def test_saida_textual_no_flat_oferece_migrate_e_nunca_repair(self) -> None:
        """O teste do guard usa `--format json` e não protegia a IMPRESSÃO:
        apagar o print de `workspace_note` o deixaria verde (Codex, r4).

        E o pior cenário é a contradição — recomendar `repair` (que cria o
        híbrido) e logo depois oferecer `migrate` na mesma saída.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            ws = Path(tmpdir)
            (ws / "_state").mkdir()
            (ws / "_state" / "workspace-schema.json").write_text("{}", encoding="utf-8")
            (ws / "PRUMO-CORE.md").write_text("> **prumo_version: 5.0.0**\n", encoding="utf-8")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update.Path.cwd",
                return_value=ws,
            ):
                rc, output = self._run_main_capturing(["update", "--check"])
        self.assertIn("migrate", output)
        self.assertNotIn("prumo repair", output, "o --check recomendou o comando que cria o híbrido")

    def test_workspace_flat_nao_dispara_repair_automatico(self) -> None:
        """#268: o repair pós-update força `layout_mode="nested"`. Rodá-lo num
        workspace flat converteria o layout do usuário como efeito colateral de
        um update de RUNTIME — dano silencioso e difícil de desfazer.

        Sem este teste, remover a supressão deixava a suíte verde (Codex, r3).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive", launcher="manual")
            ws = Path(tmpdir)
            (ws / "_state").mkdir()
            (ws / "_state" / "workspace-schema.json").write_text("{}", encoding="utf-8")
            (ws / "PRUMO-CORE.md").write_text("> **prumo_version: 5.0.0**\n", encoding="utf-8")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=(0, "5.99.0"),
            ), patch(
                "prumo_runtime.commands.update._confirm_update",
                return_value=True,
            ), patch(
                "prumo_runtime.commands.update._get_post_update_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._run_post_update_repair",
                side_effect=AssertionError("o repair NÃO pode rodar em workspace flat"),
            ), patch(
                "prumo_runtime.commands.update.Path.cwd",
                return_value=ws,
            ):
                rc, output = self._run_main_capturing(["update", "--yes", "--format", "json"])
            payload = json.loads(output)
            self.assertTrue(payload["post_update"]["workspace_detected"])
            self.assertFalse(payload["post_update"]["repair_suggested"])
            self.assertIn("migrate", payload["post_update"]["workspace_note"])


class CurlSecureTests(unittest.TestCase):
    """Testa que o caminho curl baixa pra temp file e não usa process substitution."""

    def test_missing_script_in_artifact_aborts(self) -> None:
        # #232 r5: o script vem DO artefato; staged sem scripts/ → aborta
        # (nunca baixa script avulso — _download_install_script morreu).
        from prumo_runtime.commands.update import _execute_plan

        plan = {"command": "install-script", "remote_version": "5.99.0"}
        with patch(
            "prumo_runtime.commands.update.stage_archive_source",
            return_value=("/tmp/staged-sem-script", "5.99.0", None),
        ), patch(
            "prumo_runtime.commands.update.subprocess.run"
        ) as run:
            rc, artifact_version = _execute_plan(plan, "install-script")
        self.assertEqual(rc, 1)
        self.assertIsNone(artifact_version)
        run.assert_not_called()

    def test_install_from_dir_pip_uses_sys_executable(self) -> None:
        # #232: o pip do transporte de tarball usa o MESMO Python (--user),
        # nunca um pip solto do PATH.
        from prumo_runtime.commands.update import _install_from_dir
        with patch(
            "prumo_runtime.commands.update.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as mock_run:
            rc = _install_from_dir("/tmp/staged", "pip-user")
        self.assertEqual(rc, 0)
        args = mock_run.call_args[0][0]
        self.assertIn("-m", args)
        self.assertIn("pip", args)


class UpdateCommandIntegrationTests(unittest.TestCase):
    """Testes de integração via CLI."""

    def _run_main_capturing(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_dry_run_reports_plan_without_executing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker)
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
            ) as mock_exec:
                rc, output = self._run_main_capturing(["update", "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("5.99.0", output)
            mock_exec.assert_not_called()

    def test_format_json_returns_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
            ) as mock_exec:
                rc, output = self._run_main_capturing(
                    ["update", "--dry-run", "--format", "json"]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(output)
            self.assertEqual(payload["current_version"], __version__)
            self.assertEqual(payload["remote_version"], "5.99.0")
            self.assertTrue(payload["needs_update"])
            self.assertEqual(payload["install_method"]["package_manager"], "pip-user")
            self.assertFalse(payload["plan"]["would_execute"])
            mock_exec.assert_not_called()

    def test_upgrade_alias_routes_to_update_handler(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker)
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value=__version__,
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
            ) as mock_exec:
                rc, output = self._run_main_capturing(
                    ["upgrade", "--dry-run", "--format", "json"]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(output)
            self.assertFalse(payload["needs_update"])
            mock_exec.assert_not_called()

    def test_check_reports_without_executing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker)
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
            ) as mock_exec:
                rc, output = self._run_main_capturing(["update", "--check", "--format", "json"])
            self.assertEqual(rc, 0)
            payload = json.loads(output)
            self.assertEqual(payload["remote_version"], "5.99.0")
            self.assertTrue(payload["needs_update"])
            mock_exec.assert_not_called()

    def test_offline_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker)
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value=None,
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
            ) as mock_exec:
                rc, output = self._run_main_capturing(["update", "--format", "json"])
            self.assertEqual(rc, 0)
            payload = json.loads(output)
            self.assertIsNone(payload["remote_version"])
            self.assertFalse(payload["needs_update"])
            mock_exec.assert_not_called()

    def test_channel_declared_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker)
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ):
                rc, output = self._run_main_capturing(["update", "--dry-run", "--format", "json"])
            payload = json.loads(output)
            self.assertEqual(payload["channel"], "latest em main")


class ArchiveTransportTests(unittest.TestCase):
    """#232: o transporte universal de tarball — staging validado, extração
    segura e o fim do beco do cache."""

    def _make_archive(
        self,
        base: Path,
        *,
        version: str = "5.99.0",
        pyproject_version: str | None = None,
        name: str = "prumo-runtime",
        evil_member: bool = False,
        symlink_member: bool = False,
        stray_root_member: bool = False,
    ) -> str:
        import tarfile as _tarfile

        root = base / "prumo-main"
        (root / "runtime" / "prumo_runtime").mkdir(parents=True)
        (root / "skills").mkdir()
        (root / "scripts").mkdir()
        real_script = Path(__file__).resolve().parents[2] / "scripts" / "prumo_runtime_install.sh"
        (root / "scripts" / "prumo_runtime_install.sh").write_text(
            real_script.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (root / "VERSION").write_text(version + "\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "{pyproject_version or version}"\n',
            encoding="utf-8",
        )
        archive = base / "main.tar.gz"
        with _tarfile.open(archive, "w:gz") as tar:
            tar.add(root, arcname="prumo-main")
            if evil_member:
                evil = base / "evil.txt"
                evil.write_text("x", encoding="utf-8")
                tar.add(evil, arcname="../evil.txt")
            if symlink_member:
                link = _tarfile.TarInfo(name="prumo-main/atalho")
                link.type = _tarfile.SYMTYPE
                link.linkname = "VERSION"
                tar.addfile(link)
            if stray_root_member:
                stray = base / "solto.txt"
                stray.write_text("x", encoding="utf-8")
                tar.add(stray, arcname="outra-raiz/solto.txt")
        return archive.as_uri()

    def _stage(self, url: str, remote: str):
        from prumo_runtime.commands.update import stage_archive_source

        with tempfile.TemporaryDirectory() as work:
            with patch.dict(os.environ, {"PRUMO_UPDATE_ARCHIVE_URL": url}):
                return stage_archive_source(remote, Path(work))

    def test_happy_path_stages_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp))
            staged_dir, staged_version, error = self._stage(url, "5.99.0")
        self.assertIsNone(error)
        self.assertEqual(staged_version, "5.99.0")
        self.assertIsNotNone(staged_dir)

    def test_version_mismatch_any_direction_is_rejected(self) -> None:
        # Contrato ESTRITO (Codex r2): instala exatamente o que o plano
        # anunciou — main avançou vira "rode de novo", nunca surpresa.
        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), version="6.0.0")
            staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("rode `prumo update` de novo", error)
        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), version="5.1.0")
            staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("ATRASADO", error)

    def test_failed_staging_never_reaches_installer(self) -> None:
        # Codex r3: mismatch aborta ANTES de qualquer uv/pip — o instalador
        # não pode ser tocado com artefato reprovado.
        from prumo_runtime.commands.update import _execute_plan

        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), version="6.0.0")
            plan = {"command": "archive", "archive_installer": "uv", "remote_version": "5.99.0"}
            with patch.dict(os.environ, {"PRUMO_UPDATE_ARCHIVE_URL": url}), patch(
                "prumo_runtime.commands.update._install_from_dir"
            ) as installer:
                rc, artifact_version = _execute_plan(plan, "archive")
        self.assertEqual(rc, 1)
        self.assertIsNone(artifact_version)
        installer.assert_not_called()

    def test_metadata_bomb_member_count_is_capped(self) -> None:
        # Codex r2: o teto de membros age DURANTE a iteração (tar.next),
        # nunca depois de materializar tudo.
        from prumo_runtime.commands import update as upd

        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp))
            with patch.object(upd, "_MAX_MEMBERS", 2):
                staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("membros — abortado", error)

    def test_wrong_package_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), name="prumo-fake")
            staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("não é um prumo-runtime válido", error)

    def test_version_file_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), version="5.99.0", pyproject_version="5.98.0")
            staged_dir, _, error = self._stage(url, "5.98.0")
        self.assertIsNone(staged_dir)
        self.assertIn("não é um prumo-runtime válido", error)

    def test_path_traversal_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), evil_member=True)
            staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("extração do tarball falhou", error)

    def test_symlink_member_is_rejected(self) -> None:
        # Review Codex r1 (#232): o data_filter do stdlib ainda permite link
        # INTERNO — nosso preflight rejeita qualquer não-regular.
        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), symlink_member=True)
            staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("não-regular", error)

    def test_member_outside_single_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), stray_root_member=True)
            staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("raiz única", error)

    def test_oversized_download_is_aborted(self) -> None:
        from prumo_runtime.commands import update as upd

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            url = self._make_archive(base)
            with patch.object(upd, "_MAX_ARCHIVE_BYTES", 16):
                staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("teto de download", error)

    def test_unpacked_total_over_ceiling_is_aborted(self) -> None:
        from prumo_runtime.commands import update as upd

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            url = self._make_archive(base)
            with patch.object(upd, "_MAX_UNPACKED_BYTES", 1):
                staged_dir, _, error = self._stage(url, "5.99.0")
        self.assertIsNone(staged_dir)
        self.assertIn("extração do tarball falhou", error)

    def test_install_script_stages_first_and_mismatch_never_runs_bash(self) -> None:
        # Codex r4: o install-script era o bypass restante ("latest em main"
        # sem contrato). Agora: staging validado PRIMEIRO; mismatch aborta
        # antes de baixar/rodar o script.
        from prumo_runtime.commands.update import _execute_plan

        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), version="6.0.0")
            plan = {"command": "install-script", "remote_version": "5.99.0"}
            with patch.dict(os.environ, {"PRUMO_UPDATE_ARCHIVE_URL": url}), patch(
                "prumo_runtime.commands.update.subprocess.run"
            ) as run:
                rc, artifact_version = _execute_plan(plan, "install-script")
        self.assertEqual(rc, 1)
        self.assertIsNone(artifact_version)
        run.assert_not_called()

    def test_install_script_runs_from_validated_artifact(self) -> None:
        # Codex r5: o script vem DO ARTEFATO validado (zero download extra,
        # nem do próprio script) com PRUMO_INSTALL_SOURCE_DIR apontando o
        # diretório staged.
        from prumo_runtime.commands.update import _execute_plan

        with tempfile.TemporaryDirectory() as tmp:
            url = self._make_archive(Path(tmp), version="5.99.0")
            plan = {"command": "install-script", "remote_version": "5.99.0"}
            with patch.dict(os.environ, {"PRUMO_UPDATE_ARCHIVE_URL": url}), patch(
                "prumo_runtime.commands.update.subprocess.run",
                return_value=MagicMock(returncode=0),
            ) as run:
                rc, artifact_version = _execute_plan(plan, "install-script")
        self.assertEqual(rc, 0)
        self.assertEqual(artifact_version, "5.99.0")
        args = run.call_args[0][0]
        self.assertEqual(args[0], "bash")
        self.assertIn("prumo_runtime_install.sh", args[1])
        env = run.call_args.kwargs["env"]
        self.assertIn("PRUMO_INSTALL_SOURCE_DIR", env)
        self.assertIn(env["PRUMO_INSTALL_SOURCE_DIR"], args[1])

    @unittest.skipUnless(os.name == "posix", "integração exige bash")
    def test_install_script_source_dir_mode_end_to_end(self) -> None:
        # Codex r5: Bash REAL + uv/curl falsos — zero download adicional,
        # instalação por CÓPIA (nunca --editable de um tmp) e marker
        # source_kind=archive/launcher=install-script.
        import subprocess as _subprocess

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._make_archive(base, version="5.99.0")
            source_dir = base / "prumo-main"
            bin_dir = base / "bin"
            bin_dir.mkdir()
            uv_log = base / "uv-args.txt"
            (bin_dir / "uv").write_text(
                "#!/usr/bin/env bash\n"
                f'if [ "$1" = "tool" ]; then echo "$@" >> {uv_log}; exit 0; fi\n'
                'if [ "$1" = "python" ]; then echo /usr/bin/python3.11; exit 0; fi\n'
                "exit 0\n",
                encoding="utf-8",
            )
            (bin_dir / "curl").write_text(
                "#!/usr/bin/env bash\necho 'curl chamado — download proibido' >&2\nexit 97\n",
                encoding="utf-8",
            )
            for stub in ("uv", "curl"):
                (bin_dir / stub).chmod(0o755)
            data_home = base / "xdg"
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "PRUMO_INSTALL_SOURCE_DIR": str(source_dir),
                "XDG_DATA_HOME": str(data_home),
            }
            result = _subprocess.run(
                ["bash", str(source_dir / "scripts" / "prumo_runtime_install.sh")],
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            uv_args = uv_log.read_text(encoding="utf-8")
            self.assertIn("tool install --force", uv_args)
            self.assertNotIn("--editable", uv_args, "tmp staged instalado como editable")
            self.assertNotIn("curl chamado", result.stderr, "houve download adicional")
            marker = json.loads(
                (data_home / "prumo" / "install-method.json").read_text(encoding="utf-8")
            )
            self.assertEqual(marker["source_kind"], "archive")
            self.assertEqual(marker["launcher"], "install-script")
            self.assertEqual(marker["installed_version"], "5.99.0")

    def test_copy_install_without_cached_version_falls_back_to_archive(self) -> None:
        # O beco morto do caso real do dono (#232): cache sem a versão nova
        # agora cai no tarball, nunca em plano sem comando.
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="copy",
            launcher="uv",
            local_source_dir=None,
            local_install=True,
        )
        self.assertTrue(plan["needs_update"])
        self.assertEqual(plan["command"], "archive")
        self.assertEqual(plan["archive_installer"], "uv")

    def test_no_plan_ever_targets_public_registry(self) -> None:
        # Guard anti-dependency-confusion (#232): NENHUMA combinação de
        # plano emite comando de registry público.
        import itertools

        managers = ("pip-user", "pipx", "uv-tool", "unknown")
        launchers = ("manual", "unknown", "uv", "install-script")
        for pm, launcher, local in itertools.product(managers, launchers, (False, True)):
            plan = build_update_plan(
                package_manager=pm,
                current_version="5.3.0",
                remote_version="5.4.0",
                source_kind="unknown",
                launcher=launcher,
                local_source_dir=None,
                local_install=local,
            )
            command = plan.get("command") or ""
            with self.subTest(pm=pm, launcher=launcher, local=local):
                self.assertNotIn("--upgrade prumo-runtime", command)
                self.assertNotIn("install --force prumo-runtime", command)
                self.assertNotEqual(command.strip(), "pip install prumo-runtime")


if __name__ == "__main__":
    unittest.main()
