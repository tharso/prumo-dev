"""#195: `prumo version-check` — o PRODUTOR do cache de versão.

Codex r2 do plano: o payload do briefing lê o cache TTL 24h, mas ninguém o
refrescava no fluxo do briefing — a skill fazia WebFetch todo dia e o cache
seguia stale. O subcomando é o produtor explícito: `--ensure-fresh` busca e
grava no máximo 1x/24h (TTL de falha 1h); sem a flag, zero rede sempre.
O painel (`prumo briefing --format json`) segue zero-rede — extensão da #158.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from prumo_runtime import __version__
from prumo_runtime.cli import main
from prumo_runtime import version_check


class VersionCheckCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        # Isola o cache global (~/.cache/prumo) num diretório descartável.
        self._env = mock.patch.dict(
            os.environ, {"XDG_CACHE_HOME": self._tmpdir.name}, clear=False
        )
        self._env.start()
        self.addCleanup(self._env.stop)

    def _run(self, argv: list[str]) -> tuple[int, dict]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = main(argv)
        return rc, json.loads(buffer.getvalue())

    def test_ensure_fresh_without_cache_fetches_and_writes(self) -> None:
        with mock.patch.object(
            version_check, "_fetch_remote_version", return_value="9.9.9"
        ) as fetch:
            rc, payload = self._run(["version-check", "--ensure-fresh"])
        self.assertEqual(rc, 0)
        fetch.assert_called_once()
        self.assertEqual(payload["source"], "fetched")
        self.assertEqual(payload["remote_version"], "9.9.9")
        self.assertEqual(payload["local_version"], __version__)
        self.assertTrue(payload["update_available"])
        self.assertTrue(payload["fresh"])
        # O cache foi persistido — próxima leitura não precisa de rede.
        self.assertEqual(version_check.read_cached_remote_version(), "9.9.9")

    def test_ensure_fresh_with_fresh_cache_does_not_touch_network(self) -> None:
        with mock.patch.object(
            version_check, "_fetch_remote_version", return_value=__version__
        ):
            self._run(["version-check", "--ensure-fresh"])
        boom = mock.patch.object(
            version_check,
            "_fetch_remote_version",
            side_effect=AssertionError("rede chamada com cache fresco"),
        )
        with boom:
            rc, payload = self._run(["version-check", "--ensure-fresh"])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["source"], "cache")
        self.assertTrue(payload["fresh"])
        self.assertFalse(payload["update_available"])

    def test_ensure_fresh_records_failure_and_does_not_block(self) -> None:
        with mock.patch.object(
            version_check, "_fetch_remote_version", return_value=None
        ):
            rc, payload = self._run(["version-check", "--ensure-fresh"])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["source"], "fetch_failed")
        self.assertIsNone(payload["remote_version"])
        self.assertFalse(payload["update_available"])
        # Falha registrada com TTL curto: o cache existe e está marcado.
        cache = version_check._read_cache(version_check._cache_path())
        self.assertIsNotNone(cache)
        self.assertTrue(cache.get("failed"))

    def test_without_ensure_fresh_never_fetches(self) -> None:
        boom = mock.patch.object(
            version_check,
            "_fetch_remote_version",
            side_effect=AssertionError("version-check sem --ensure-fresh tocou a rede"),
        )
        with boom:
            rc, payload = self._run(["version-check"])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["source"], "no_cache")
        self.assertFalse(payload["fresh"])
        self.assertIsNone(payload["remote_version"])

    def test_version_check_is_banner_suppressed(self) -> None:
        # O comando É a checagem; o banner em cima seria eco.
        self.assertIn("version-check", version_check.SUPPRESS_COMMANDS)


if __name__ == "__main__":
    unittest.main()
