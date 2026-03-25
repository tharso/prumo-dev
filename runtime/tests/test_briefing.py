from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
from unittest.mock import patch

from prumo_runtime.commands.briefing import (
    build_briefing_payload,
    choose_proposal,
    enrich_snapshot_with_apple_reminders,
    load_snapshot_cache,
    run_briefing,
    resolve_snapshot_data,
    summarize_apple_reminders_status,
    summarize_google_status,
    summarize_emails,
    write_snapshot_cache,
)
from prumo_runtime import __version__
from prumo_runtime.google_api import is_actionworthy_triage_item
from prumo_runtime.platform_support import platform_label


class BriefingSnapshotTests(unittest.TestCase):
    def test_build_briefing_payload_exposes_sections_and_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            inbox_dir = workspace / "Inbox4Mobile"
            state_dir.mkdir(parents=True, exist_ok=True)
            inbox_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "PAUTA.md").write_text(
                "# Pauta\n\n## Quente (precisa de atenção agora)\n\n- Ajuste urgente no site\n\n"
                "## Em andamento\n\n- Projeto X\n\n## Agendado / Lembretes\n\n- Revisão semanal\n",
                encoding="utf-8",
            )
            (workspace / "INBOX.md").write_text("# Inbox\n\n_Inbox limpo._\n", encoding="utf-8")
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
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
            (state_dir / "briefing-state.json").write_text('{"last_briefing_at": ""}', encoding="utf-8")
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            previous = os.environ.get("PRUMO_RUNTIME_DISABLE_SNAPSHOT")
            os.environ["PRUMO_RUNTIME_DISABLE_SNAPSHOT"] = "1"
            try:
                payload = build_briefing_payload(workspace, refresh_snapshot=False)
            finally:
                if previous is None:
                    os.environ.pop("PRUMO_RUNTIME_DISABLE_SNAPSHOT", None)
                else:
                    os.environ["PRUMO_RUNTIME_DISABLE_SNAPSHOT"] = previous
            self.assertEqual(payload["workspace_path"], str(workspace.resolve()))
            self.assertTrue(payload["sections"])
            self.assertEqual(payload["sections"][0]["id"], "preflight")
            self.assertEqual(payload["proposal"]["options"][0]["id"], "continue")
            self.assertIn("Proposta do dia", payload["message"])
            self.assertIn("actions", payload)
            self.assertFalse(any(action["id"] == "workflow-scaffold" for action in payload["actions"]))
            self.assertEqual(payload["daily_operation"]["mode"], "daily-operator")
            self.assertTrue(payload["capabilities"]["daily_operation"]["documentation"])
            self.assertIn("documentation_contract", payload["daily_operation"])
            self.assertEqual(payload["next_move"]["id"], "continue")

    def test_run_briefing_json_output_uses_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            inbox_dir = workspace / "Inbox4Mobile"
            state_dir.mkdir(parents=True, exist_ok=True)
            inbox_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "PAUTA.md").write_text(
                "# Pauta\n\n## Quente (precisa de atenção agora)\n\n- Ajuste urgente no site\n",
                encoding="utf-8",
            )
            (workspace / "INBOX.md").write_text("# Inbox\n\n_Inbox limpo._\n", encoding="utf-8")
            (workspace / "PRUMO-CORE.md").write_text(f"> **prumo_version: {__version__}**\n", encoding="utf-8")
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
            (state_dir / "briefing-state.json").write_text('{"last_briefing_at": ""}', encoding="utf-8")
            (state_dir / "google-integration.json").write_text("{}", encoding="utf-8")
            (state_dir / "apple-reminders-integration.json").write_text("{}", encoding="utf-8")
            args = Namespace(workspace=str(workspace), refresh_snapshot=False, format="json")
            buffer = io.StringIO()
            previous = os.environ.get("PRUMO_RUNTIME_DISABLE_SNAPSHOT")
            os.environ["PRUMO_RUNTIME_DISABLE_SNAPSHOT"] = "1"
            try:
                with redirect_stdout(buffer):
                    rc = run_briefing(args)
            finally:
                if previous is None:
                    os.environ.pop("PRUMO_RUNTIME_DISABLE_SNAPSHOT", None)
                else:
                    os.environ["PRUMO_RUNTIME_DISABLE_SNAPSHOT"] = previous
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["workspace_path"], str(workspace.resolve()))
            self.assertIn("sections", payload)
            self.assertEqual(payload["sections"][0]["label"], "Preflight")
            self.assertIn("proposal", payload)
            self.assertIn("actions", payload)
            self.assertIn("next_move", payload)
            self.assertIn("selection_contract", payload)
            self.assertEqual(payload["platform"]["label"], platform_label())
            self.assertFalse(any(section["id"] == "workflow_scaffolding" for section in payload["sections"]))
            self.assertTrue(any("documentation_targets" in action for action in payload["actions"]))
            self.assertEqual(payload["selection_contract"]["accepts_next_move"], "continue")
            self.assertIn("aceitar", payload["selection_contract"]["accept_tokens"])

    def test_write_and_load_snapshot_cache_preserves_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            snapshot = {
                "ok_profiles": 1,
                "profiles": {
                    "pessoal": {
                        "emails_total": 2,
                        "triage_reply": [],
                        "triage_view": ["P2 | 09:00 | Danilo | Assunto | preview"],
                        "triage_no_action": [],
                    }
                },
                "source": "google-direct-api",
                "note": "fonte direta respondeu bem",
                "email_note": "email veio direto da Gmail API",
                "email_display": "Email veio direto da Gmail API.",
            }
            write_snapshot_cache(workspace, "America/Sao_Paulo", snapshot)
            payload = load_snapshot_cache(workspace, "America/Sao_Paulo")
            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertEqual(payload["source"], "google-direct-api")
            self.assertIn("fonte direta respondeu bem", payload["note"])
            self.assertEqual(payload["email_note"], "email veio direto da Gmail API")
            self.assertEqual(payload["email_display"], "Email veio direto da Gmail API.")

    @patch("prumo_runtime.commands.briefing.write_snapshot_cache")
    @patch("prumo_runtime.commands.briefing.fetch_google_workspace_snapshot")
    @patch("prumo_runtime.commands.briefing.connected_google_profile", return_value="pessoal")
    def test_resolve_snapshot_data_prefers_direct_google_snapshot(
        self,
        _mock_profile,
        mock_direct_snapshot,
        mock_write_cache,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            mock_direct_snapshot.return_value = {
                "ok_profiles": 1,
                "profiles": {"pessoal": {"emails_total": 1}},
                "source": "google-direct-api",
                "note": "",
                "email_note": "direto",
                "email_display": "Direto.",
            }
            payload = resolve_snapshot_data(workspace, repo_root=None, refresh_snapshot=True)
            self.assertEqual(payload["source"], "google-direct-api")
            self.assertEqual(payload["email_note"], "direto")
            self.assertEqual(payload["email_display"], "Direto.")
            self.assertIn("cached_at", payload)
            mock_write_cache.assert_called_once()

    @patch("prumo_runtime.commands.briefing.run_dual_snapshot")
    @patch("prumo_runtime.commands.briefing.fetch_google_workspace_snapshot", side_effect=RuntimeError("boom"))
    @patch("prumo_runtime.commands.briefing.connected_google_profile", return_value="pessoal")
    def test_resolve_snapshot_data_uses_cache_when_direct_api_fails(
        self,
        _mock_profile,
        _mock_direct_snapshot,
        mock_dual_snapshot,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            write_snapshot_cache(
                workspace,
                "America/Sao_Paulo",
                {
                    "ok_profiles": 1,
                    "profiles": {},
                    "source": "google-direct-api",
                    "note": "cache decente",
                    "email_note": "cache email",
                    "email_display": "Cache email.",
                },
            )
            payload = resolve_snapshot_data(workspace, repo_root=None, refresh_snapshot=True)
            self.assertEqual(payload["status"], "cache")
            self.assertIn("Google API falhou (boom); usei cache.", payload["note"])
            mock_dual_snapshot.assert_not_called()

    @patch("prumo_runtime.commands.briefing.run_dual_snapshot")
    @patch("prumo_runtime.commands.briefing.fetch_google_workspace_snapshot", side_effect=RuntimeError("boom"))
    @patch("prumo_runtime.commands.briefing.connected_google_profile", return_value="pessoal")
    def test_resolve_snapshot_data_falls_back_to_dual_snapshot_without_cache(
        self,
        _mock_profile,
        _mock_direct_snapshot,
        mock_dual_snapshot,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            mock_dual_snapshot.return_value = {
                "ok_profiles": 1,
                "profiles": {"pessoal": {"emails_total": 1}},
                "note": "fallback ainda respirava.",
                "email_note": "dual",
                "email_display": "Fallback dual.",
                "source": "google-dual-snapshot",
            }
            payload = resolve_snapshot_data(workspace, repo_root=None, refresh_snapshot=True)
            self.assertEqual(payload["source"], "google-dual-snapshot")
            self.assertIn("Google API falhou (boom).", payload["note"])
            mock_dual_snapshot.assert_called_once()

    def test_summarize_emails_uses_email_note_for_empty_snapshot(self) -> None:
        rendered = summarize_emails(
            {
                "ok_profiles": 0,
                "profiles": {},
                "email_note": "email direto ainda nao entrou",
                "note": "sem cache",
            }
        )
        self.assertEqual(rendered, "email direto ainda nao entrou")

    def test_summarize_emails_explicitly_reports_zero_messages(self) -> None:
        rendered = summarize_emails(
            {
                "ok_profiles": 1,
                "profiles": {
                    "pessoal": {
                        "emails_total": 0,
                        "triage_reply": [],
                        "triage_view": [],
                        "triage_no_action": [],
                    }
                },
                "email_note": "Gmail API respondeu vazio; pelo menos desta vez foi vazio honesto.",
                "email_display": "Nenhum email novo.",
            }
        )
        self.assertIn("Nenhum email novo", rendered)
        self.assertIn("Gmail API respondeu vazio", rendered)

    def test_summarize_google_status_reports_refresh_and_reauth(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "google-integration.json").write_text(
                json.dumps(
                    {
                        "status": "connected",
                        "active_profile": "pessoal",
                        "profiles": {
                            "pessoal": {
                                "status": "connected",
                                "account_email": "batata@example.com",
                                "last_authenticated_at": "2026-03-19T19:53:00-03:00",
                                "last_refresh_at": "2026-03-19T20:03:00-03:00",
                                "last_error": "",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            rendered = summarize_google_status(workspace, "America/Sao_Paulo")
            self.assertIn("conectado", rendered)
            self.assertIn("batata@example.com", rendered)
            self.assertIn("20:03", rendered)
            self.assertRegex(rendered, r"(min atrás|h\d{2} atrás|h atrás)")

            (state_dir / "google-integration.json").write_text(
                json.dumps(
                    {
                        "status": "needs_reauth",
                        "active_profile": "pessoal",
                        "profiles": {
                            "pessoal": {
                                "status": "needs_reauth",
                                "account_email": "batata@example.com",
                                "last_error": "Google pediu reautenticacao.",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            rendered = summarize_google_status(workspace, "America/Sao_Paulo")
            self.assertIn("precisa reautenticar", rendered)
            self.assertIn("prumo auth google", rendered)

    def test_summarize_apple_reminders_status_reports_connected_and_disconnected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "apple-reminders-integration.json").write_text(
                json.dumps(
                    {
                        "status": "connected",
                        "authorization_status": "fullAccess",
                        "last_refresh_at": "2026-03-20T15:13:00-03:00",
                        "lists": ["A vida...", "Família"],
                    }
                ),
                encoding="utf-8",
            )
            rendered = summarize_apple_reminders_status(workspace, "America/Sao_Paulo")
            self.assertIn("conectado", rendered)
            self.assertIn("2 lista(s)", rendered)
            self.assertIn("15:13", rendered)
            self.assertIn("fora do foco desta fase", rendered)

            (state_dir / "apple-reminders-integration.json").write_text(
                json.dumps(
                    {
                        "status": "disconnected",
                        "authorization_status": "denied",
                        "last_error": "Apple negou acesso",
                        "lists": [],
                    }
                ),
                encoding="utf-8",
            )
            rendered = summarize_apple_reminders_status(workspace, "America/Sao_Paulo")
            self.assertIn("desconectado", rendered)
            self.assertIn("backlog desta fase", rendered)
            self.assertIn("Apple negou acesso", rendered)

    @patch(
        "prumo_runtime.commands.briefing.fetch_apple_reminders_today",
        return_value={
            "status": "ok",
            "items": ["16:00 | [Apple Reminders] Teste Prumo (A vida...)"],
            "note": "Apple Reminders via EventKit.",
        },
    )
    @patch(
        "prumo_runtime.commands.briefing.apple_reminders_summary",
        return_value={"status": "connected"},
    )
    def test_enrich_snapshot_with_apple_reminders_adds_local_profile(
        self,
        _mock_summary,
        _mock_fetch,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            snapshot = {
                "ok_profiles": 1,
                "profiles": {
                    "pessoal": {
                        "status": "OK",
                        "account": "tharso@gmail.com",
                        "agenda_today": [],
                        "agenda_tomorrow": [],
                        "emails_total": 0,
                        "triage_reply": [],
                        "triage_view": [],
                        "triage_no_action": [],
                        "errors": [],
                    }
                },
                "note": "agenda veio direto da Google Calendar API.",
            }
            enriched = enrich_snapshot_with_apple_reminders(workspace, "America/Sao_Paulo", snapshot)
            self.assertIn("apple-reminders", enriched["profiles"])
            self.assertEqual(enriched["ok_profiles"], 2)
            self.assertEqual(
                enriched["profiles"]["apple-reminders"]["agenda_today"],
                ["16:00 | [Apple Reminders] Teste Prumo (A vida...)"],
            )

    @patch(
        "prumo_runtime.commands.briefing.fetch_apple_reminders_today",
        return_value={
            "status": "cache",
            "items": [],
            "note": "Cache local de Apple Reminders reaproveitado (4 min atrás).",
        },
    )
    @patch(
        "prumo_runtime.commands.briefing.apple_reminders_summary",
        return_value={"status": "connected"},
    )
    def test_enrich_snapshot_with_apple_reminders_preserves_note_and_refresh_flag(
        self,
        _mock_summary,
        mock_fetch,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            snapshot = {"ok_profiles": 0, "profiles": {}, "note": "agenda veio do Google."}
            enriched = enrich_snapshot_with_apple_reminders(
                workspace,
                "America/Sao_Paulo",
                snapshot,
                refresh_snapshot=True,
            )
            self.assertIn("Cache local de Apple Reminders reaproveitado", enriched["note"])
            mock_fetch.assert_called_once_with(
                workspace,
                "America/Sao_Paulo",
                refresh=True,
            )

    def test_choose_proposal_ignores_low_signal_email_before_andamento(self) -> None:
        proposal = choose_proposal(
            [],
            [],
            ["Decidir abertura de empresa"],
            {
                "profiles": {
                    "pessoal": {
                        "triage_reply": [],
                        "triage_view": [
                            "P2 | 19:23 | Google Cloud | You have upgraded to a paid Google Cloud account | Explore full access"
                        ],
                    }
                }
            },
        )
        self.assertEqual(proposal, "Decidir abertura de empresa")

    def test_actionworthy_triage_item_accepts_p1_and_rejects_billing_noise(self) -> None:
        self.assertTrue(is_actionworthy_triage_item("P1 | 09:00 | Danilo | Ajuste urgente no site | revisar"))
        self.assertFalse(
            is_actionworthy_triage_item(
                "P2 | 19:23 | Google Cloud | You have upgraded to a paid Google Cloud account | Explore full access"
            )
        )


if __name__ == "__main__":
    unittest.main()
