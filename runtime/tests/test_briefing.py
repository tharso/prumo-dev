from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
import io
import os
from pathlib import Path

from prumo_runtime.commands.briefing import (
    build_briefing_payload,
    choose_proposal,
    list_or_placeholder,
    run_briefing,
    shorten_pauta_item,
)
from prumo_runtime import __version__
from prumo_runtime.platform_support import platform_label


class BriefingTests(unittest.TestCase):
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
            (state_dir / "last-briefing.json").write_text('{"at": ""}', encoding="utf-8")
            payload = build_briefing_payload(workspace)
            self.assertEqual(payload["workspace_path"], str(workspace.resolve()))
            self.assertEqual(payload["adapter_contract_version"], "2026-03-28")
            self.assertTrue(payload["sections"])
            self.assertEqual(payload["sections"][0]["id"], "preflight")
            self.assertTrue(payload["canonical_refs"]["briefing_procedure"].endswith("modules/briefing-procedure.md"))
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
            (state_dir / "last-briefing.json").write_text('{"at": ""}', encoding="utf-8")
            args = Namespace(workspace=str(workspace), format="json")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_briefing(args)
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["workspace_path"], str(workspace.resolve()))
            self.assertEqual(payload["adapter_contract_version"], "2026-03-28")
            self.assertIn("sections", payload)
            self.assertEqual(payload["sections"][0]["label"], "Preflight")
            self.assertTrue(payload["canonical_refs"]["inbox_processing"].endswith("modules/inbox-processing.md"))
            self.assertIn("proposal", payload)
            self.assertIn("actions", payload)
            self.assertIn("next_move", payload)
            self.assertIn("selection_contract", payload)
            self.assertIn("degradation", payload)
            self.assertEqual(payload["platform"]["label"], platform_label())
            self.assertFalse(any(section["id"] == "workflow_scaffolding" for section in payload["sections"]))
            self.assertFalse(any(section["id"] == "apple_reminders" for section in payload["sections"]))
            self.assertTrue(any("documentation_targets" in action for action in payload["actions"]))
            self.assertEqual(payload["selection_contract"]["accepts_next_move"], "continue")
            self.assertIn("aceitar", payload["selection_contract"]["accept_tokens"])

    def test_briefing_surfaces_align_core_as_named_option_when_core_outdated(self) -> None:
        """Quando o core está defasado, o menu do briefing deve mostrar 'Atualizar o motor' pelo nome, com o comando."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "PRUMO-CORE.md").write_text("> **prumo_version: 4.0.0**\n", encoding="utf-8")
            (workspace / "PAUTA.md").write_text(
                "# Pauta\n\n## Em andamento\n\n- Projeto X\n",
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
            (state_dir / "last-briefing.json").write_text('{"at": ""}', encoding="utf-8")
            payload = build_briefing_payload(workspace)
            self.assertTrue(payload["core_outdated"])
            self.assertIn("Atualizar o motor", payload["message"])
            self.assertIn("prumo migrate", payload["message"])

    def test_briefing_menu_shows_named_alternatives_not_collapsed_lista(self) -> None:
        """Com next_move definido, o menu do briefing não pode colapsar em 'Ver lista completa'. Tem que exibir alternativas nomeadas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / "_state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "PRUMO-CORE.md").write_text(
                f"> **prumo_version: {__version__}**\n", encoding="utf-8"
            )
            (workspace / "PAUTA.md").write_text(
                "# Pauta\n\n## Quente (precisa de atenção agora)\n\n- Ajuste urgente\n",
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
            (state_dir / "last-briefing.json").write_text('{"at": ""}', encoding="utf-8")
            payload = build_briefing_payload(workspace)
            message = payload["message"]
            self.assertNotIn("Ver lista completa", message)
            named_alternatives = [
                "Rodar o briefing",
                "Organizar o dia",
                "estado técnico",
            ]
            visible = sum(1 for marker in named_alternatives if marker in message)
            self.assertGreaterEqual(visible, 2)

    def test_choose_proposal_prefers_quente_over_andamento(self) -> None:
        proposal = choose_proposal(
            ["Ajuste urgente"],
            ["Agendado X"],
            ["Decidir abertura de empresa"],
        )
        self.assertEqual(proposal, "Ajuste urgente")

    def test_choose_proposal_falls_back_to_andamento(self) -> None:
        proposal = choose_proposal(
            [],
            [],
            ["Decidir abertura de empresa"],
        )
        self.assertEqual(proposal, "Decidir abertura de empresa")

    def test_choose_proposal_returns_fallback_when_empty(self) -> None:
        proposal = choose_proposal([], [], [])
        self.assertIn("dump real de pendências", proposal)


class ShortenPautaItemTests(unittest.TestCase):
    def test_keeps_tag_title_and_cobrar_suffix(self) -> None:
        item = (
            "- [Pai] **Reunião Emilie — Encontro da Aprendizagem Solidária (Nina)** "
            "— Sexta 24/04, 13:30–15h, Sala de Projeção. Convocação da Sonia. "
            "(desde 22/04) | cobrar: 23/04"
        )
        self.assertEqual(
            shorten_pauta_item(item),
            "[Pai] **Reunião Emilie — Encontro da Aprendizagem Solidária (Nina)** | cobrar: 23/04",
        )

    def test_drops_descriptive_tail_when_no_cobrar(self) -> None:
        item = (
            "- [Pessoal/Financeiro] **Declaração de IR 2026** — Prazo até 29/05. "
            "Documentos enviados ao contador (confirmado 22/04)."
        )
        self.assertEqual(
            shorten_pauta_item(item),
            "[Pessoal/Financeiro] **Declaração de IR 2026**",
        )

    def test_falls_back_to_char_truncate_when_no_bold_title(self) -> None:
        item = "- [Pai] reuniao da escola amanha as 19h, levar caderno do Roque e conversar com a tia"
        result = shorten_pauta_item(item, max_fallback_chars=80)
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 84)
        self.assertTrue(result.startswith("[Pai] reuniao"))

    def test_fallback_preserves_cobrar_suffix(self) -> None:
        item = "- [Pai] reuniao curta sem destaque (desde 14/04) | cobrar: 25/04"
        result = shorten_pauta_item(item)
        self.assertIn("| cobrar: 25/04", result)
        self.assertTrue(result.startswith("[Pai] reuniao curta sem destaque (desde 14/04)"))

    def test_handles_item_without_bullet_prefix(self) -> None:
        item = "[Pessoal] **Comprar parafuso M5x30** — Yoga confirmou ontem"
        self.assertEqual(
            shorten_pauta_item(item),
            "[Pessoal] **Comprar parafuso M5x30**",
        )


class ListOrPlaceholderTests(unittest.TestCase):
    def test_returns_fallback_when_empty(self) -> None:
        self.assertEqual(
            list_or_placeholder([], "Pauta sem tração aparente."),
            "Pauta sem tração aparente.",
        )

    def test_appends_overflow_count_when_more_than_limit(self) -> None:
        items = [
            "- [A] **Item 1** — descricao 1",
            "- [B] **Item 2** — descricao 2",
            "- [C] **Item 3** — descricao 3",
            "- [D] **Item 4** — descricao 4",
            "- [E] **Item 5** — descricao 5",
        ]
        result = list_or_placeholder(items, "fallback")
        self.assertIn("[A] **Item 1**", result)
        self.assertIn("[C] **Item 3**", result)
        self.assertNotIn("Item 4", result)
        self.assertTrue(result.endswith(" (+2)"))

    def test_no_overflow_suffix_when_at_or_below_limit(self) -> None:
        items = [
            "- [A] **Item 1** — descricao 1",
            "- [B] **Item 2** — descricao 2",
        ]
        result = list_or_placeholder(items, "fallback")
        self.assertNotIn("(+", result)

    def test_shortens_each_item(self) -> None:
        items = [
            "- [Pai] **Reunião Emilie** — descricao longa que deveria sumir do panorama final",
        ]
        result = list_or_placeholder(items, "fallback")
        self.assertEqual(result, "[Pai] **Reunião Emilie**")


if __name__ == "__main__":
    unittest.main()
