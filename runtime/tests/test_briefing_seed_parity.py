"""Oráculo diferencial da semente (#197).

A MESMA fixture é processada pelos dois caminhos — leitura direta dos .md
(o que o `briefing-procedure.md` fazia) e o payload do runtime — e o panorama
resultante tem que ser o MESMO. Se o payload perder qualquer coisa que o
caminho direto enxerga (item, marker, seção, hibernando, cauda do registro),
este teste quebra antes de o procedure confiar na semente.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from prumo_runtime import __version__
from prumo_runtime.commands.briefing import build_briefing_payload, count_inbox_items
from prumo_runtime.pauta_parsing import extract_section, filter_by_due_date

PAUTA = """# Pauta

## Quente (precisa de atenção agora)

- **Pagar boleto** | cobrar: {today}
- **Cobrar proposta** | cobrar: {tomorrow}
- **Item futuro** | cobrar: {future}
- **Item atrasado** | cobrar: {overdue}
- **Marker quebrado** | cobrar: qualquer dia desses
- **Sem marker nenhum**
- **Quarto item além do top-3 do cartão antigo**

## Em andamento

- Projeto X com contexto longo que a curadoria precisa ver inteiro pra ponte associativa funcionar

## Agendado / Lembretes

- Revisão semanal | cobrar: {future}

## Hibernando

- **Ideia adormecida** com [[conexao]]
- Segunda ideia hibernada
"""


def _build_workspace(tmpdir: str) -> tuple[Path, str, str]:
    workspace = Path(tmpdir)
    state_dir = workspace / "_state"
    inbox_dir = workspace / "Inbox4Mobile"
    state_dir.mkdir(parents=True)
    inbox_dir.mkdir(parents=True)
    tz = "America/Sao_Paulo"
    today = datetime.now(ZoneInfo(tz)).date()
    from datetime import timedelta

    def dm(delta: int) -> str:
        d = today + timedelta(days=delta)
        return f"{d.day:02d}/{d.month:02d}/{d.year}"

    pauta_text = PAUTA.format(
        today=dm(0), tomorrow=dm(1), future=dm(5), overdue=dm(-3)
    )
    (workspace / "PAUTA.md").write_text(pauta_text, encoding="utf-8")
    inbox_text = "# Inbox\n\n- item um\n- item dois\n"
    (workspace / "INBOX.md").write_text(inbox_text, encoding="utf-8")
    (workspace / "REGISTRO.md").write_text(
        "# Registro\n\n| Data | Item |\n|---|---|\n"
        + "\n".join(f"| {i:02d}/07 | linha {i} |" for i in range(1, 15))
        + "\n",
        encoding="utf-8",
    )
    (state_dir / "workspace-schema.json").write_text(
        json.dumps(
            {
                "user_name": "Batata",
                "agent_name": "Prumo",
                "timezone": tz,
                "briefing_time": "09:00",
                "files": {"generated": [], "authorial": [], "derived": []},
            }
        ),
        encoding="utf-8",
    )
    (workspace / "PRUMO-CORE.md").write_text(
        f"> **prumo_version: {__version__}**\n", encoding="utf-8"
    )
    return workspace, pauta_text, inbox_text


class SeedParityTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="prumo-parity-")
        self.addCleanup(self._tmp.cleanup)
        self.ws, self.pauta_text, self.inbox_text = _build_workspace(self._tmp.name)
        self.payload = build_briefing_payload(self.ws)
        self.panorama = self.payload["local_panorama"]
        self.by_id = {s["id"]: s for s in self.panorama["pauta"]["sections"]}
        self.today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    def test_visible_items_match_direct_path_per_section(self) -> None:
        for section_id, heading in (
            ("quente", "Quente"),
            ("em_andamento", "Em andamento"),
            ("agendado", "Agendado"),
        ):
            direct = filter_by_due_date(
                extract_section(self.pauta_text, heading), self.today
            )
            seed = [
                item["text"]
                for item in self.by_id[section_id]["items"]
                if item["visible_today"]
            ]
            self.assertEqual(seed, direct, f"paridade quebrada na seção {heading}")

    def test_all_items_present_including_invisible_future(self) -> None:
        direct_all = extract_section(self.pauta_text, "Quente")
        seed_all = [item["text"] for item in self.by_id["quente"]["items"]]
        self.assertEqual(seed_all, direct_all, "payload não pode perder item nenhum")
        self.assertGreater(len(seed_all), 3, "cenário exige mais itens que o top-3 antigo")

    def test_hibernando_parity_for_associative_bridge(self) -> None:
        direct = extract_section(self.pauta_text, "Hibernando")
        seed = [item["text"] for item in self.by_id["hibernando"]["items"]]
        self.assertEqual(seed, direct)
        self.assertIn("[[conexao]]", seed[0])

    def test_cobrar_states_cover_all_categories(self) -> None:
        states = {
            item["cobrar"]["state"]
            for item in self.by_id["quente"]["items"]
            if item.get("cobrar") is not None
        }
        self.assertEqual(states, {"today", "tomorrow", "future", "overdue", "invalid"})

    def test_invalid_marker_fail_open_matches_direct(self) -> None:
        broken = next(
            item
            for item in self.by_id["quente"]["items"]
            if item.get("cobrar") and item["cobrar"]["state"] == "invalid"
        )
        self.assertTrue(broken["visible_today"])
        self.assertIn(
            broken["text"],
            filter_by_due_date(extract_section(self.pauta_text, "Quente"), self.today),
        )

    def test_inbox_count_parity(self) -> None:
        self.assertEqual(
            self.panorama["inbox"]["count"], count_inbox_items(self.inbox_text)
        )

    def test_registro_tail_present_for_bridge(self) -> None:
        tail = self.panorama["registro"]["tail"]
        self.assertTrue(tail)
        self.assertIn("linha 14", tail[-1])

    def test_generated_for_uses_workspace_timezone(self) -> None:
        self.assertEqual(self.panorama["generated_for"], self.today.isoformat())

    def test_completeness_all_sources_ok(self) -> None:
        completeness = self.payload["payload_completeness"]
        for source in ("pauta", "inbox", "registro"):
            self.assertTrue(completeness[source]["complete"], source)


class SeedReadOnlyTest(unittest.TestCase):
    def test_briefing_payload_never_spawns_preview_subprocess(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prumo-seed-ro-") as tmp:
            ws, _, _ = _build_workspace(tmp)
            (ws / "Inbox4Mobile" / "captura.md").write_text("- algo\n", encoding="utf-8")
            with mock.patch(
                "prumo_runtime.inbox_preview.subprocess.run",
                side_effect=AssertionError("a semente regenerou o preview"),
            ):
                payload = build_briefing_payload(ws)
        self.assertIn(payload["local_panorama"]["inbox4mobile"]["status"], {"ausente", "stale"})

    def test_stale_index_is_reported_not_regenerated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prumo-seed-stale-") as tmp:
            ws, _, _ = _build_workspace(tmp)
            import os
            import time

            index = ws / "Inbox4Mobile" / "_preview-index.json"
            index_payload = {"items": [{"filename": "velho.md", "kind": "text"}]}
            index.write_text(json.dumps(index_payload), encoding="utf-8")
            old = time.time() - 3600
            os.utime(index, (old, old))
            (ws / "Inbox4Mobile" / "novo.md").write_text("- novo\n", encoding="utf-8")
            payload = build_briefing_payload(ws)
            block = payload["local_panorama"]["inbox4mobile"]
            self.assertEqual(block["status"], "stale")
            self.assertFalse(
                payload["payload_completeness"]["inbox4mobile"]["complete"],
                "stale tem que sinalizar incompletude da fonte",
            )

    def test_missing_pauta_signals_source_and_keeps_others(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prumo-seed-partial-") as tmp:
            ws, _, inbox_text = _build_workspace(tmp)
            (ws / "PAUTA.md").unlink()
            payload = build_briefing_payload(ws)
            completeness = payload["payload_completeness"]
            self.assertFalse(completeness["pauta"]["complete"])
            self.assertTrue(completeness["inbox"]["complete"])
            self.assertEqual(
                payload["local_panorama"]["inbox"]["count"],
                count_inbox_items(inbox_text),
            )


if __name__ == "__main__":
    unittest.main()
