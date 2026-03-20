from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prumo_runtime.apple_reminders import (
    fetch_apple_reminders_today,
    helper_script_path,
    load_apple_reminders,
    load_apple_reminders_snapshot,
    parse_applescript_output,
    set_observed_apple_reminders_lists,
)


class AppleRemindersTests(unittest.TestCase):
    def test_parse_applescript_output_supports_tabbed_item_payload(self) -> None:
        payload = parse_applescript_output(
            "\n".join(
                [
                    "STATUS:ok",
                    "AUTHORIZATION:authorized",
                    "LIST:A vida...",
                    "ITEM:Teste Prumo\tA vida...\t16:00\t16:00 | [Apple Reminders] Teste Prumo (A vida...)",
                    "NOTE:Apple Reminders via AppleScript nas listas observadas.",
                ]
            )
        )
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["authorization_status"], "authorized")
        self.assertEqual(payload["lists"], ["A vida..."])
        self.assertEqual(payload["today"][0]["title"], "Teste Prumo")
        self.assertEqual(payload["today"][0]["list"], "A vida...")
        self.assertEqual(payload["today"][0]["label"], "16:00")

    def test_helper_script_path_resolves_from_repo_not_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            helper = helper_script_path(workspace)
            self.assertTrue(helper.name == "apple_reminders.swift")
            self.assertIn("/runtime/prumo_runtime/helpers/", str(helper))

    def test_set_observed_lists_persists_cleaned_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload = set_observed_apple_reminders_lists(
                workspace,
                "America/Sao_Paulo",
                [" A vida... ", "", "Família"],
            )
            self.assertEqual(payload["observed_lists"], ["A vida...", "Família"])
            state = load_apple_reminders(workspace)
            self.assertEqual(state["observed_lists"], ["A vida...", "Família"])

    @patch(
        "prumo_runtime.apple_reminders.run_apple_reminders_helper",
        return_value={
            "status": "ok",
            "authorization_status": "fullAccess",
            "lists": ["A vida..."],
            "today": [
                {
                    "title": "Teste Prumo",
                    "list": "A vida...",
                    "display": "16:00 | [Apple Reminders] Teste Prumo (A vida...)",
                }
            ],
            "note": "Apple Reminders via EventKit.",
        },
    )
    def test_fetch_apple_reminders_today_updates_state(self, _mock_helper) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload = fetch_apple_reminders_today(workspace, "America/Sao_Paulo")
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["items"], ["16:00 | [Apple Reminders] Teste Prumo (A vida...)"])
            state = load_apple_reminders(workspace)
            self.assertEqual(state["status"], "connected")
            self.assertEqual(state["authorization_status"], "fullAccess")
            self.assertEqual(state["lists"], ["A vida..."])

    @patch("prumo_runtime.apple_reminders.run_apple_reminders_helper")
    def test_fetch_apple_reminders_today_reuses_fresh_cache(self, mock_helper) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            first_payload = {
                "status": "ok",
                "authorization_status": "fullAccess",
                "lists": ["A vida..."],
                "today": [
                    {
                        "title": "Teste Prumo",
                        "list": "A vida...",
                        "display": "16:00 | [Apple Reminders] Teste Prumo (A vida...)",
                    }
                ],
                "note": "Apple Reminders via EventKit.",
            }
            mock_helper.return_value = first_payload
            initial = fetch_apple_reminders_today(workspace, "America/Sao_Paulo", refresh=True)
            cached = fetch_apple_reminders_today(workspace, "America/Sao_Paulo", refresh=False)
            self.assertEqual(initial["status"], "ok")
            self.assertEqual(cached["status"], "cache")
            self.assertIn("Cache local de Apple Reminders reaproveitado", cached["note"])
            self.assertEqual(mock_helper.call_count, 1)
            snapshot = load_apple_reminders_snapshot(workspace)
            self.assertEqual(snapshot["status"], "ok")
            self.assertEqual(snapshot["items"], ["16:00 | [Apple Reminders] Teste Prumo (A vida...)"])


if __name__ == "__main__":
    unittest.main()
