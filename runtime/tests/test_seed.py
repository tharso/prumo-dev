"""`prumo seed` — a semente em arquivo pra hosts sem runtime (#216, opção b)."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from prumo_runtime import __version__
from prumo_runtime.commands.seed import (
    SEED_SCHEMA_VERSION,
    build_seed_payload,
    run_seed,
    seed_file_path,
    write_seed,
)


def _build_workspace(tmpdir: str) -> Path:
    workspace = Path(tmpdir)
    state_dir = workspace / "_state"
    (workspace / "Inbox4Mobile").mkdir(parents=True)
    state_dir.mkdir(parents=True)
    (workspace / ".prumo").mkdir()
    (workspace / "PAUTA.md").write_text(
        "# Pauta\n\n## Quente\n\n- **Item A** | cobrar: 26/07\n\n"
        "## Em andamento\n\n- Projeto X\n\n## Agendado\n\n- Revisão\n\n"
        "## Hibernando\n\n- Ideia\n\n## Horizonte\n\n- Aposta\n",
        encoding="utf-8",
    )
    (workspace / "INBOX.md").write_text("# Inbox\n\n- um\n", encoding="utf-8")
    (workspace / "REGISTRO.md").write_text(
        "# Registro\n\n| Data | Item |\n|---|---|\n| 01/07 | linha |\n",
        encoding="utf-8",
    )
    (state_dir / "workspace-schema.json").write_text(
        json.dumps(
            {
                "user_name": "Batata",
                "agent_name": "Prumo",
                "timezone": "America/Sao_Paulo",
                "briefing_time": "09:00",
                "files": {"generated": [], "authorial": [], "derived": []},
            }
        ),
        encoding="utf-8",
    )
    (workspace / "PRUMO-CORE.md").write_text(
        f"> **prumo_version: {__version__}**\n", encoding="utf-8"
    )
    return workspace


class SeedPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="prumo-seed-")
        self.addCleanup(self._tmp.cleanup)
        self.ws = _build_workspace(self._tmp.name)

    def test_payload_schema_and_content_matches_live_seed(self) -> None:
        payload = build_seed_payload(self.ws)
        self.assertEqual(payload["schema_version"], SEED_SCHEMA_VERSION)
        panorama = payload["local_panorama"]
        self.assertEqual(panorama["schema_version"], "prumo_local_panorama.v1")
        self.assertIsInstance(panorama["pauta"]["outras_secoes"], list)
        self.assertEqual(
            [s["label"] for s in panorama["pauta"]["outras_secoes"]], ["Horizonte"]
        )
        self.assertIn("payload_completeness", payload)
        for source in ("pauta", "inbox", "registro", "processed"):
            self.assertIn(source, payload["payload_completeness"])

    def test_source_mtimes_match_real_files(self) -> None:
        payload = build_seed_payload(self.ws)
        mtimes = payload["source_mtimes"]
        for key, path in (
            ("pauta", self.ws / "PAUTA.md"),
            ("inbox", self.ws / "INBOX.md"),
            ("registro", self.ws / "REGISTRO.md"),
        ):
            self.assertEqual(
                mtimes[key]["mtime_ns"], path.stat().st_mtime_ns, key
            )
            self.assertIn("mtime", mtimes[key], "ISO de segundos pro consumo do agente")
        self.assertIsNone(mtimes["processed"], "sem _processed.json → None")

    def test_inbox4mobile_manifest_lists_every_content_file(self) -> None:
        inbox = self.ws / "Inbox4Mobile"
        (inbox / "captura-a.md").write_text("- a\n", encoding="utf-8")
        (inbox / "captura-b.md").write_text("- b\n", encoding="utf-8")
        (inbox / "inbox-preview.html").write_text("<html></html>", encoding="utf-8")
        payload = build_seed_payload(self.ws)
        manifest = payload["inbox4mobile_manifest"]
        names = [e["name"] for e in manifest]
        self.assertEqual(names, ["captura-a.md", "captura-b.md"])
        for entry in manifest:
            self.assertIn("size", entry)
            self.assertIn("mtime", entry)
            self.assertIn("mtime_ns", entry)

    def test_source_changed_mid_generation_retries_then_aborts(self) -> None:
        from prumo_runtime.commands import seed as seed_mod

        real_build = seed_mod._build_once
        pauta = self.ws / "PAUTA.md"

        def mutating_build(workspace, paths, tz):
            result = real_build(workspace, paths, tz)
            pauta.write_text(
                pauta.read_text(encoding="utf-8") + "\n- item novo\n",
                encoding="utf-8",
            )
            return result

        with mock.patch.object(seed_mod, "_build_once", side_effect=mutating_build):
            with self.assertRaises(seed_mod.SeedError):
                build_seed_payload(self.ws)

    def test_inbox_mutation_mid_generation_aborts(self) -> None:
        from prumo_runtime.commands import seed as seed_mod

        real_build = seed_mod._build_once
        inbox = self.ws / "Inbox4Mobile"

        def mutating_build(workspace, paths, tz):
            result = real_build(workspace, paths, tz)
            (inbox / "chegou-no-meio.md").write_text("- x\n", encoding="utf-8")
            return result

        with mock.patch.object(seed_mod, "_build_once", side_effect=mutating_build):
            with self.assertRaises(seed_mod.SeedError):
                build_seed_payload(self.ws)

    def test_inbox_listing_failure_is_visible_error(self) -> None:
        from prumo_runtime.commands import seed as seed_mod

        real_iterdir = Path.iterdir

        def failing_iterdir(self_path):
            if self_path.name == "Inbox4Mobile":
                raise OSError("negado simulado")
            return real_iterdir(self_path)

        with mock.patch.object(Path, "iterdir", failing_iterdir):
            with self.assertRaises(seed_mod.SeedError):
                build_seed_payload(self.ws)

    def test_symlinked_state_refuses_write(self) -> None:
        import shutil as _sh

        from prumo_runtime.commands.seed import SeedError

        outside = Path(self._tmp.name) / "state-externo"
        outside.mkdir()
        state = self.ws / ".prumo" / "state"
        if state.exists():
            _sh.rmtree(state)
        state.symlink_to(outside)
        external_before = sorted(p.name for p in outside.iterdir())
        with self.assertRaises(SeedError):
            write_seed(self.ws)
        self.assertEqual(
            sorted(p.name for p in outside.iterdir()),
            external_before,
            "escrita atravessou o symlink",
        )

    def test_seed_generation_is_read_only_over_sources(self) -> None:
        before = {
            p: p.stat().st_mtime_ns
            for p in (
                self.ws / "PAUTA.md",
                self.ws / "INBOX.md",
                self.ws / "REGISTRO.md",
            )
        }
        with mock.patch(
            "prumo_runtime.inbox_preview.subprocess.run",
            side_effect=AssertionError("seed regenerou o preview"),
        ):
            build_seed_payload(self.ws)
        for p, mtime in before.items():
            self.assertEqual(p.stat().st_mtime_ns, mtime, f"{p.name} foi tocado")

    def test_write_seed_is_atomic_and_parseable(self) -> None:
        target = write_seed(self.ws)
        self.assertEqual(target, seed_file_path(self.ws))
        payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], SEED_SCHEMA_VERSION)
        leftovers = list(target.parent.glob("*.tmp"))
        self.assertEqual(leftovers, [], "temp de escrita ficou pra trás")

    def test_generated_at_is_utc_and_recent(self) -> None:
        payload = build_seed_payload(self.ws)
        generated = datetime.fromisoformat(payload["generated_at"])
        self.assertIsNotNone(generated.tzinfo)
        now = datetime.now(ZoneInfo("UTC"))
        self.assertLess(abs((now - generated).total_seconds()), 60)


class SeedCliTests(unittest.TestCase):
    def test_run_seed_writes_and_reports(self) -> None:
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory(prefix="prumo-seed-cli-") as tmp:
            ws = _build_workspace(tmp)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = run_seed(Namespace(workspace=str(ws), format="text"))
            self.assertEqual(code, 0)
            out = buffer.getvalue()
            self.assertIn("semente gravada", out)
            self.assertIn("local-panorama.json", out)
            self.assertTrue(seed_file_path(ws).exists())

    def test_run_seed_without_prumo_dir_fails_politely(self) -> None:
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory(prefix="prumo-seed-nows-") as tmp:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = run_seed(Namespace(workspace=tmp, format="text"))
            self.assertEqual(code, 1)
            self.assertIn("sem `.prumo/`", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
