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

    def test_pip_user_returns_pip_install_command(self) -> None:
        plan = build_update_plan(
            package_manager="pip-user",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="archive",
        )
        self.assertTrue(plan["needs_update"])
        self.assertIn("pip", plan["command"])
        self.assertIn("install", plan["command"])

    def test_uv_tool_returns_uv_command(self) -> None:
        plan = build_update_plan(
            package_manager="uv-tool",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="archive",
        )
        self.assertTrue(plan["needs_update"])
        self.assertIn("uv", plan["command"])

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

    def test_unknown_method_returns_manual_instruction(self) -> None:
        plan = build_update_plan(
            package_manager="unknown",
            current_version="5.3.0",
            remote_version="5.4.0",
            source_kind="unknown",
        )
        self.assertTrue(plan["needs_update"])
        self.assertIsNone(plan["command"])
        self.assertIn("manualmente", plan["explanation"].lower())

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
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=0,
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
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=0,
            ), patch(
                "prumo_runtime.commands.update._confirm_update",
                return_value=True,
            ) as mock_confirm:
                rc, _ = self._run_main_capturing(["update"])
            mock_confirm.assert_called_once()

    def test_confirm_rejected_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=0,
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
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=0,
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
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
                return_value=0,
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

    def test_workspace_detected_suggests_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker_v1(marker, package_manager="pip-user", source_kind="archive")
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
                return_value=0,
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


class CurlSecureTests(unittest.TestCase):
    """Testa que o caminho curl baixa pra temp file e não usa process substitution."""

    def test_execute_plan_curl_uses_temp_file(self) -> None:
        from prumo_runtime.commands.update import _execute_plan
        plan = {
            "command": "install-script",
            "explanation": "test",
        }
        with patch(
            "prumo_runtime.commands.update._download_install_script",
            return_value="/tmp/fake_script.sh",
        ) as mock_dl, patch(
            "prumo_runtime.commands.update.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as mock_run, patch(
            "prumo_runtime.commands.update.os.unlink",
        ) as mock_unlink:
            rc = _execute_plan(plan, "install-script")
        mock_dl.assert_called_once()
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "bash")
        self.assertEqual(args[1], "/tmp/fake_script.sh")
        self.assertNotIn("-c", args)
        mock_unlink.assert_called_once()

    def test_execute_plan_pip_uses_sys_executable(self) -> None:
        from prumo_runtime.commands.update import _execute_plan
        plan = {
            "command": "pip install --upgrade prumo-runtime",
            "explanation": "test",
        }
        with patch(
            "prumo_runtime.commands.update.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as mock_run:
            rc = _execute_plan(plan, "pip-user")
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


if __name__ == "__main__":
    unittest.main()
