"""
Testes do version check automático (#87).

Cobre: cache TTL, cache de falha, cooldown de banner, supressões,
comparação semver, offline gracioso, escrita atômica.
"""
from __future__ import annotations

import io
import json
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch, MagicMock

from prumo_runtime import __version__
from prumo_runtime.version_check import (
    check_and_notify,
    _cache_path,
    _read_cache,
    _write_cache,
    _should_suppress,
    _should_fetch,
    _should_show_banner,
)


class CachePathTests(unittest.TestCase):
    def test_xdg_compliant_on_unix(self) -> None:
        with patch.dict("os.environ", {"XDG_CACHE_HOME": "/tmp/xdg-cache"}, clear=False):
            with patch("prumo_runtime.version_check.sys.platform", "linux"):
                path = _cache_path()
                self.assertEqual(path, Path("/tmp/xdg-cache/prumo/version-check.json"))

    def test_localappdata_on_windows(self) -> None:
        with patch.dict("os.environ", {"LOCALAPPDATA": "C:\\Users\\test\\AppData\\Local"}, clear=False):
            with patch("prumo_runtime.version_check.sys.platform", "win32"):
                path = _cache_path()
                self.assertEqual(path, Path("C:\\Users\\test\\AppData\\Local/prumo/version-check.json"))


class CacheReadWriteTests(unittest.TestCase):
    def test_write_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "prumo" / "version-check.json"
            data = {"remote_version": "5.4.0", "checked_at": "2026-05-05T20:00:00Z"}
            _write_cache(data, path)
            result = _read_cache(path)
            self.assertEqual(result["remote_version"], "5.4.0")

    def test_read_missing_returns_none(self) -> None:
        result = _read_cache(Path("/nonexistent/path.json"))
        self.assertIsNone(result)

    def test_read_corrupt_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "cache.json"
            path.write_text("not json {", encoding="utf-8")
            result = _read_cache(path)
            self.assertIsNone(result)


class ShouldSuppressTests(unittest.TestCase):
    def test_prumo_no_version_check_env(self) -> None:
        with patch.dict("os.environ", {"PRUMO_NO_VERSION_CHECK": "1"}):
            self.assertTrue(_should_suppress(command="start", format_arg="text"))

    def test_ci_env(self) -> None:
        with patch.dict("os.environ", {"CI": "true"}):
            self.assertTrue(_should_suppress(command="start", format_arg="text"))

    def test_noninteractive_env(self) -> None:
        with patch.dict("os.environ", {"PRUMO_NONINTERACTIVE": "1"}):
            self.assertTrue(_should_suppress(command="start", format_arg="text"))

    def test_format_json_suppresses(self) -> None:
        self.assertTrue(_should_suppress(command="start", format_arg="json"))

    def test_update_command_suppresses(self) -> None:
        self.assertTrue(_should_suppress(command="update", format_arg="text"))

    def test_upgrade_command_suppresses(self) -> None:
        self.assertTrue(_should_suppress(command="upgrade", format_arg="text"))

    def test_version_command_suppresses(self) -> None:
        self.assertTrue(_should_suppress(command="version", format_arg="text"))

    def test_stderr_not_tty_suppresses(self) -> None:
        with patch("prumo_runtime.version_check.sys.stderr") as mock_stderr:
            mock_stderr.isatty.return_value = False
            self.assertTrue(_should_suppress(command="start", format_arg="text"))

    def test_normal_interactive_does_not_suppress(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("prumo_runtime.version_check.sys.stderr") as mock_stderr:
                mock_stderr.isatty.return_value = True
                self.assertFalse(_should_suppress(command="start", format_arg="text"))


class ShouldFetchTests(unittest.TestCase):
    def test_no_cache_should_fetch(self) -> None:
        self.assertTrue(_should_fetch(None))

    def test_fresh_cache_should_not_fetch(self) -> None:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cache = {"checked_at": now, "remote_version": "5.3.0"}
        self.assertFalse(_should_fetch(cache, ttl_hours=24))

    def test_expired_cache_should_fetch(self) -> None:
        old = "2020-01-01T00:00:00+00:00"
        cache = {"checked_at": old, "remote_version": "5.3.0"}
        self.assertTrue(_should_fetch(cache, ttl_hours=24))

    def test_failed_cache_with_short_ttl(self) -> None:
        old = "2020-01-01T00:00:00+00:00"
        cache = {"checked_at": old, "remote_version": None, "failed": True}
        self.assertTrue(_should_fetch(cache, ttl_hours=24))

    def test_recent_failure_respects_failure_ttl(self) -> None:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cache = {"checked_at": now, "remote_version": None, "failed": True}
        self.assertFalse(_should_fetch(cache, ttl_hours=24))


class ShouldShowBannerTests(unittest.TestCase):
    def test_newer_remote_shows_banner(self) -> None:
        self.assertTrue(_should_show_banner("5.4.0", "5.3.0", None))

    def test_same_version_no_banner(self) -> None:
        self.assertFalse(_should_show_banner("5.3.0", "5.3.0", None))

    def test_older_remote_no_banner(self) -> None:
        self.assertFalse(_should_show_banner("5.2.0", "5.3.0", None))

    def test_remote_none_no_banner(self) -> None:
        self.assertFalse(_should_show_banner(None, "5.3.0", None))

    def test_cooldown_suppresses_banner(self) -> None:
        import datetime
        recent = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.assertFalse(_should_show_banner("5.4.0", "5.3.0", recent))

    def test_old_notification_allows_banner(self) -> None:
        old = "2020-01-01T00:00:00+00:00"
        self.assertTrue(_should_show_banner("5.4.0", "5.3.0", old))


class CheckAndNotifyIntegrationTests(unittest.TestCase):
    def test_banner_emitted_to_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "prumo" / "version-check.json"
            buf = io.StringIO()
            with patch("prumo_runtime.version_check._cache_path", return_value=cache_file), \
                 patch("prumo_runtime.version_check._should_suppress", return_value=False), \
                 patch("prumo_runtime.version_check._fetch_remote_version", return_value="9.9.9"), \
                 redirect_stderr(buf):
                check_and_notify(command="start", format_arg="text")
            output = buf.getvalue()
            self.assertIn("9.9.9", output)
            self.assertIn("prumo update", output)

    def test_suppressed_no_output(self) -> None:
        buf = io.StringIO()
        with patch("prumo_runtime.version_check._should_suppress", return_value=True), \
             redirect_stderr(buf):
            check_and_notify(command="start", format_arg="json")
        self.assertEqual(buf.getvalue(), "")

    def test_offline_no_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "prumo" / "version-check.json"
            buf = io.StringIO()
            with patch("prumo_runtime.version_check._cache_path", return_value=cache_file), \
                 patch("prumo_runtime.version_check._should_suppress", return_value=False), \
                 patch("prumo_runtime.version_check._fetch_remote_version", return_value=None), \
                 redirect_stderr(buf):
                check_and_notify(command="start", format_arg="text")
            self.assertEqual(buf.getvalue(), "")

    def test_cache_written_after_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "prumo" / "version-check.json"
            with patch("prumo_runtime.version_check._cache_path", return_value=cache_file), \
                 patch("prumo_runtime.version_check._should_suppress", return_value=False), \
                 patch("prumo_runtime.version_check._fetch_remote_version", return_value="5.3.0"), \
                 redirect_stderr(io.StringIO()):
                check_and_notify(command="start", format_arg="text")
            self.assertTrue(cache_file.exists())
            data = json.loads(cache_file.read_text())
            self.assertEqual(data["remote_version"], "5.3.0")

    def test_cache_hit_does_not_fetch(self) -> None:
        import datetime
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "prumo" / "version-check.json"
            cache_file.parent.mkdir(parents=True)
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cache_file.write_text(json.dumps({
                "checked_at": now,
                "remote_version": "5.3.0",
                "last_notified_at": None,
            }))
            with patch("prumo_runtime.version_check._cache_path", return_value=cache_file), \
                 patch("prumo_runtime.version_check._should_suppress", return_value=False), \
                 patch("prumo_runtime.version_check._fetch_remote_version") as mock_fetch, \
                 redirect_stderr(io.StringIO()):
                check_and_notify(command="start", format_arg="text")
            mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
