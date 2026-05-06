"""
Testes do comando `prumo update` (#86).

Cobre detecção de método de instalação (marker JSON ou fallback pip),
geração de plano, formato JSON pra hosts, alias `prumo upgrade`, e
modos `--check`/`--dry-run` que **não** executam update real.

Update real **não roda em CI** — todos os testes que tocam `run_update`
ficam em `--dry-run` ou `--check`.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from prumo_runtime import __version__
from prumo_runtime.cli import main
from prumo_runtime.commands.update import (
    build_update_plan,
    detect_install_method,
    install_marker_path,
)


def _write_marker(path: Path, method: str, source: str = "https://example") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "method": method,
                "source": source,
                "installed_at": "2026-05-05T20:00:00Z",
            }
        ),
        encoding="utf-8",
    )


class DetectInstallMethodTests(unittest.TestCase):
    def test_reads_curl_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker(marker, "curl")
            result = detect_install_method(marker)
            self.assertEqual(result["method"], "curl")
            self.assertEqual(result["source"], "marker")

    def test_reads_pip_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker(marker, "pip")
            result = detect_install_method(marker)
            self.assertEqual(result["method"], "pip")
            self.assertEqual(result["source"], "marker")

    def test_corrupt_marker_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            marker.write_text("not json {", encoding="utf-8")
            with patch("prumo_runtime.commands.update.shutil.which", return_value=None):
                result = detect_install_method(marker)
            self.assertEqual(result["source"], "fallback")

    def test_no_marker_falls_back_to_pip_when_pip_show_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            absent_marker = Path(tmpdir) / "install-method.json"
            mock_proc = MagicMock(returncode=0, stdout="Name: prumo-runtime", stderr="")
            with patch(
                "prumo_runtime.commands.update.shutil.which",
                return_value="/usr/bin/pip",
            ), patch(
                "prumo_runtime.commands.update.subprocess.run",
                return_value=mock_proc,
            ):
                result = detect_install_method(absent_marker)
            self.assertEqual(result["method"], "pip")
            self.assertEqual(result["source"], "fallback")

    def test_no_marker_no_pip_show_returns_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            absent_marker = Path(tmpdir) / "install-method.json"
            with patch(
                "prumo_runtime.commands.update.shutil.which",
                return_value=None,
            ):
                result = detect_install_method(absent_marker)
            self.assertEqual(result["method"], "unknown")
            self.assertEqual(result["source"], "fallback")

    def test_install_marker_path_is_xdg_compliant_on_unix(self) -> None:
        with patch.dict("os.environ", {"XDG_DATA_HOME": "/tmp/xdg-test"}, clear=False):
            with patch("prumo_runtime.commands.update.sys.platform", "linux"):
                path = install_marker_path()
                self.assertEqual(
                    path,
                    Path("/tmp/xdg-test") / "prumo" / "install-method.json",
                )


class BuildUpdatePlanTests(unittest.TestCase):
    def test_pip_method_returns_pip_install_command(self) -> None:
        plan = build_update_plan(method="pip", current_version="5.3.0", remote_version="5.4.0")
        self.assertTrue(plan["needs_update"])
        self.assertIn("pip install --upgrade prumo-runtime", plan["command"])

    def test_curl_method_returns_install_script_url(self) -> None:
        plan = build_update_plan(method="curl", current_version="5.3.0", remote_version="5.4.0")
        self.assertTrue(plan["needs_update"])
        self.assertIn("prumo_runtime_install.sh", plan["command"])

    def test_no_update_needed_when_versions_match(self) -> None:
        plan = build_update_plan(method="pip", current_version="5.3.0", remote_version="5.3.0")
        self.assertFalse(plan["needs_update"])
        self.assertIsNone(plan["command"])

    def test_remote_version_none_means_offline_and_no_plan(self) -> None:
        plan = build_update_plan(method="pip", current_version="5.3.0", remote_version=None)
        self.assertFalse(plan["needs_update"])
        self.assertIsNone(plan["command"])
        self.assertIn("offline", plan["explanation"].lower())

    def test_unknown_method_returns_command_none_with_manual_instruction(self) -> None:
        plan = build_update_plan(method="unknown", current_version="5.3.0", remote_version="5.4.0")
        self.assertTrue(plan["needs_update"])
        self.assertIsNone(plan["command"])
        self.assertIn("pip install", plan["explanation"])
        self.assertIn("install script", plan["explanation"].lower())


class UpdateCommandIntegrationTests(unittest.TestCase):
    def _run_main_capturing(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_dry_run_with_curl_marker_reports_plan_without_executing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker(marker, "curl")
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
            self.assertIn("prumo_runtime_install.sh", output)
            mock_exec.assert_not_called()

    def test_format_json_returns_machine_readable_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker(marker, "pip")
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
            self.assertEqual(payload["install_method"], "pip")
            self.assertEqual(payload["install_method_source"], "marker")
            self.assertIn("pip install --upgrade prumo-runtime", payload["plan"]["command"])
            self.assertFalse(payload["plan"]["would_execute"])
            mock_exec.assert_not_called()

    def test_upgrade_alias_routes_to_update_handler(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker(marker, "pip")
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

    def test_check_only_reports_remote_version_without_executing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker(marker, "pip")
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
            self.assertFalse(payload["plan"]["would_execute"])
            mock_exec.assert_not_called()

    def test_offline_does_not_execute_or_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "install-method.json"
            _write_marker(marker, "pip")
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=marker,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value=None,  # simula falha de rede
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
            ) as mock_exec:
                rc, output = self._run_main_capturing(["update", "--format", "json"])
            self.assertEqual(rc, 0)
            payload = json.loads(output)
            self.assertIsNone(payload["remote_version"])
            self.assertFalse(payload["needs_update"])
            self.assertFalse(payload["plan"]["would_execute"])
            mock_exec.assert_not_called()

    def test_unknown_method_does_not_execute_and_returns_nonzero(self) -> None:
        # Sem marker e sem pip → method=unknown → command=None → não executa, rc=1
        with tempfile.TemporaryDirectory() as tmpdir:
            absent_marker = Path(tmpdir) / "install-method.json"
            with patch(
                "prumo_runtime.commands.update.install_marker_path",
                return_value=absent_marker,
            ), patch(
                "prumo_runtime.commands.update.shutil.which",
                return_value=None,
            ), patch(
                "prumo_runtime.commands.update.fetch_remote_version",
                return_value="5.99.0",
            ), patch(
                "prumo_runtime.commands.update._execute_plan",
            ) as mock_exec:
                rc, output = self._run_main_capturing(["update", "--format", "json"])
            self.assertEqual(rc, 1)
            payload = json.loads(output)
            self.assertEqual(payload["install_method"], "unknown")
            self.assertTrue(payload["needs_update"])
            self.assertIsNone(payload["plan"]["command"])
            mock_exec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
