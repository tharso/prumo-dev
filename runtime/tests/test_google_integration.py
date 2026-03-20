from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prumo_runtime.google_integration import (
    DEFAULT_GOOGLE_PROFILE,
    DEFAULT_GOOGLE_SCOPES,
    default_google_integration_payload,
    google_integration_summary,
    load_google_integration,
    resolve_token_storage,
    update_profile_state,
)


class GoogleIntegrationTests(unittest.TestCase):
    def test_default_payload_starts_disconnected_with_pessoal_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload = default_google_integration_payload(workspace)
            self.assertEqual(payload["status"], "disconnected")
            self.assertEqual(payload["active_profile"], DEFAULT_GOOGLE_PROFILE)
            self.assertIn(DEFAULT_GOOGLE_PROFILE, payload["profiles"])
            self.assertIn("https://www.googleapis.com/auth/tasks.readonly", DEFAULT_GOOGLE_SCOPES)

    def test_load_google_integration_merges_defaults_into_partial_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            target = workspace / "_state" / "google-integration.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(
                    {
                        "status": "connected",
                        "profiles": {
                            "pessoal": {
                                "status": "connected",
                                "account_email": "batata@example.com",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            payload = load_google_integration(workspace)
            profile = payload["profiles"]["pessoal"]
            self.assertEqual(payload["status"], "connected")
            self.assertEqual(profile["account_email"], "batata@example.com")
            self.assertEqual(profile["source"], "browser-oauth")
            self.assertIn("token_storage", profile)

    def test_update_profile_state_persists_connected_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload = update_profile_state(
                workspace,
                "pessoal",
                status="connected",
                account_email="batata@example.com",
                scopes=["openid", "email"],
                last_authenticated_at="2026-03-19T12:00:00-03:00",
                last_refresh_at="2026-03-19T12:05:00-03:00",
            )
            profile = payload["profiles"]["pessoal"]
            self.assertEqual(payload["status"], "connected")
            self.assertEqual(payload["active_profile"], "pessoal")
            self.assertEqual(profile["account_email"], "batata@example.com")
            self.assertEqual(profile["last_authenticated_at"], "2026-03-19T12:00:00-03:00")
            self.assertEqual(profile["last_refresh_at"], "2026-03-19T12:05:00-03:00")
            self.assertEqual(profile["last_error"], "")

    def test_google_integration_summary_exposes_active_profile_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            update_profile_state(
                workspace,
                "pessoal",
                status="needs_reauth",
                account_email="batata@example.com",
                scopes=["openid", "email"],
                last_authenticated_at="2026-03-19T19:53:00-03:00",
                last_refresh_at="2026-03-19T20:03:00-03:00",
                last_error="Google pediu reauth.",
            )
            payload = google_integration_summary(workspace)
            self.assertEqual(payload["active_profile_status"], "needs_reauth")
            self.assertEqual(payload["active_account_email"], "batata@example.com")
            self.assertEqual(payload["active_last_refresh_at"], "2026-03-19T20:03:00-03:00")
            self.assertEqual(payload["active_last_error"], "Google pediu reauth.")

    @patch("prumo_runtime.google_integration.keychain_supported", return_value=True)
    def test_resolve_token_storage_prefers_saved_storage(self, _mock_supported) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            target = workspace / "_state" / "google-integration.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(
                    {
                        "profiles": {
                            "pessoal": {
                                "token_storage": {
                                    "type": "macos-keychain",
                                    "service": "svc.custom",
                                    "account": "acc.custom",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            storage = resolve_token_storage(workspace, "pessoal")
            self.assertEqual(storage["service"], "svc.custom")
            self.assertEqual(storage["account"], "acc.custom")


if __name__ == "__main__":
    unittest.main()
