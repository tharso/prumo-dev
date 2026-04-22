from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from prumo_runtime.workspace import (
    migrate_briefing_state_to_last_briefing,
    update_last_briefing,
)
from prumo_runtime.workspace_paths import workspace_paths


class LastBriefingSchemaTests(unittest.TestCase):
    def test_update_last_briefing_writes_slim_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            paths = workspace_paths(workspace)
            paths.state_root.mkdir(parents=True, exist_ok=True)

            update_last_briefing(workspace, "America/Sao_Paulo")

            payload = json.loads(paths.last_briefing.read_text(encoding="utf-8"))
            self.assertEqual(set(payload.keys()), {"at"})
            self.assertTrue(payload["at"])

    def test_update_last_briefing_overwrites_previous_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            paths = workspace_paths(workspace)
            paths.state_root.mkdir(parents=True, exist_ok=True)
            paths.last_briefing.write_text('{"at": "2020-01-01T00:00:00"}', encoding="utf-8")

            update_last_briefing(workspace, "America/Sao_Paulo")

            payload = json.loads(paths.last_briefing.read_text(encoding="utf-8"))
            self.assertNotEqual(payload["at"], "2020-01-01T00:00:00")


class LastBriefingMigrationTests(unittest.TestCase):
    def test_migration_converts_old_file_and_deletes_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            paths = workspace_paths(workspace)
            paths.state_root.mkdir(parents=True, exist_ok=True)
            old_path = paths.state_root / "briefing-state.json"
            old_path.write_text(
                json.dumps({
                    "last_briefing_at": "2026-04-20T10:30:00-03:00",
                    "interrupted_at": "",
                    "resume_point": "",
                }),
                encoding="utf-8",
            )

            migrate_briefing_state_to_last_briefing(workspace)

            self.assertFalse(old_path.exists())
            self.assertTrue(paths.last_briefing.exists())
            payload = json.loads(paths.last_briefing.read_text(encoding="utf-8"))
            self.assertEqual(payload, {"at": "2026-04-20T10:30:00-03:00"})

    def test_migration_handles_old_file_with_empty_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            paths = workspace_paths(workspace)
            paths.state_root.mkdir(parents=True, exist_ok=True)
            old_path = paths.state_root / "briefing-state.json"
            old_path.write_text('{"last_briefing_at": ""}', encoding="utf-8")

            migrate_briefing_state_to_last_briefing(workspace)

            self.assertFalse(old_path.exists())
            self.assertTrue(paths.last_briefing.exists())
            payload = json.loads(paths.last_briefing.read_text(encoding="utf-8"))
            self.assertEqual(payload, {"at": ""})

    def test_migration_is_noop_when_nothing_to_migrate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            paths = workspace_paths(workspace)
            paths.state_root.mkdir(parents=True, exist_ok=True)

            migrate_briefing_state_to_last_briefing(workspace)

            self.assertFalse(paths.last_briefing.exists())

    def test_migration_does_not_overwrite_existing_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            paths = workspace_paths(workspace)
            paths.state_root.mkdir(parents=True, exist_ok=True)
            paths.last_briefing.write_text(
                '{"at": "2026-04-21T09:00:00-03:00"}',
                encoding="utf-8",
            )
            old_path = paths.state_root / "briefing-state.json"
            old_path.write_text(
                '{"last_briefing_at": "2026-04-20T10:00:00-03:00"}',
                encoding="utf-8",
            )

            migrate_briefing_state_to_last_briefing(workspace)

            self.assertFalse(old_path.exists())
            payload = json.loads(paths.last_briefing.read_text(encoding="utf-8"))
            self.assertEqual(payload["at"], "2026-04-21T09:00:00-03:00")


if __name__ == "__main__":
    unittest.main()
