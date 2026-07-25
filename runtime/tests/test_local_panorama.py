"""Panorama local estruturado + completude por fonte (#197)."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from prumo_runtime.local_panorama import (
    PANORAMA_SCHEMA_VERSION,
    build_local_panorama,
    build_pauta_block,
)
from prumo_runtime.pauta_parsing import cobrar_state

TODAY = date(2026, 7, 25)

PAUTA = """# Pauta

## Quente

- **Item A** sem marker
- **Item B** | cobrar: 26/07
- **Item C** | cobrar: 28/07
- **Item D** | cobrar: 25/07
- **Item E** atrasado | cobrar: 20/07

## Em andamento

- Item longo demais pra caber no display sem corte porque tem muito contexto acumulado de decisões anteriores e vírgulas — precisa aparecer inteiro no text e cortado no display_text quando passar do teto de duzentos caracteres do contrato de orçamento do panorama local do briefing determinístico

## Agendado

- **Agendado 1** | cobrar: 30/12

## Hibernando

- **Projeto adormecido** com [[conexao-antiga]]
- Outro hibernado
"""


class CobrarStateTest(unittest.TestCase):
    def test_no_marker_is_none(self) -> None:
        self.assertIsNone(cobrar_state("- **X** sem marker", TODAY))

    def test_states_and_visibility(self) -> None:
        cases = {
            "- x | cobrar: 28/07": ("future", False),
            "- x | cobrar: 26/07": ("tomorrow", True),
            "- x | cobrar: 25/07": ("today", True),
            "- x | cobrar: 20/07": ("overdue", True),
        }
        for item, (state, visible) in cases.items():
            result = cobrar_state(item, TODAY)
            self.assertEqual(result["state"], state, item)
            self.assertEqual(result["visible_today"], visible, item)
            self.assertIsNotNone(result["date"])

    def test_malformed_marker_is_invalid_and_fail_open(self) -> None:
        result = cobrar_state("- x | cobrar: trinta e dois", TODAY)
        self.assertEqual(result["state"], "invalid")
        self.assertIsNone(result["date"])
        self.assertTrue(result["visible_today"], "fail-open: marker quebrado mostra o item")

    def test_year_rollover_marker_in_december(self) -> None:
        # 05/01 escrito em dezembro é janeiro do ANO SEGUINTE (horizonte 60d).
        result = cobrar_state("- x | cobrar: 05/01", date(2026, 12, 20))
        self.assertEqual(result["state"], "future")
        self.assertEqual(result["date"], "2027-01-05")


class PautaBlockTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.block = build_pauta_block(PAUTA, TODAY)
        cls.by_id = {s["id"]: s for s in cls.block["sections"]}

    def test_all_four_sections_present_including_hibernando(self) -> None:
        self.assertEqual(
            [s["id"] for s in self.block["sections"]],
            ["quente", "em_andamento", "agendado", "hibernando"],
        )
        self.assertEqual(self.by_id["hibernando"]["count"], 2)

    def test_items_carry_full_text_beyond_top3(self) -> None:
        quente = self.by_id["quente"]
        self.assertEqual(quente["count"], 5, "todos os itens, não só os 3 do cartão antigo")
        self.assertIn("sem marker", quente["items"][0]["text"])

    def test_visible_count_applies_cobrar_rule(self) -> None:
        quente = self.by_id["quente"]
        # A (sem marker), B (véspera), D (hoje), E (atrasado) visíveis; C (futuro) não.
        self.assertEqual(quente["visible_count"], 4)
        by_text = {i["text"]: i for i in quente["items"]}
        self.assertFalse(by_text["- **Item C** | cobrar: 28/07"]["visible_today"])

    def test_display_text_is_capped_but_text_is_integral(self) -> None:
        item = self.by_id["em_andamento"]["items"][0]
        self.assertTrue(item["display_text"].endswith("..."))
        self.assertLessEqual(len(item["display_text"]), 203)
        self.assertIn("briefing determinístico", item["text"], "text carrega a linha integral")

    def test_hibernando_preserves_associative_links(self) -> None:
        self.assertIn("[[conexao-antiga]]", self.by_id["hibernando"]["items"][0]["text"])


class BuildLocalPanoramaTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="prumo-panorama-")
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.pauta = root / "PAUTA.md"
        self.inbox = root / "INBOX.md"
        self.registro = root / "REGISTRO.md"
        self.processed = root / "_processed.json"
        self.pauta.write_text(PAUTA, encoding="utf-8")
        # "12. três" e não "1. três": o contador atual só reconhece numerados
        # de DOIS dígitos (paridade é com o comportamento real, não o ideal).
        self.inbox.write_text("# Inbox\n\n- um\n- dois\n12. três\n", encoding="utf-8")
        self.registro.write_text(
            "# Registro\n\n| Data | Item |\n|---|---|\n"
            + "\n".join(f"| 0{i}/07 | linha {i} |" for i in range(1, 8))
            + "\n",
            encoding="utf-8",
        )
        self.processed.write_text(
            json.dumps(
                {
                    "items": [
                        {"filename": "a.md", "processed_at": "2026-07-24T10:00:00"},
                        {"filename": "b.md", "processed_at": "2026-06-01T10:00:00"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.preview = {
            "status": "gerado",
            "note": "",
            "count": 2,
            "freshness": {"index_mtime": "2026-07-25T09:00:00+00:00"},
            "index_present": True,
        }

    def _build(self, **overrides):
        kwargs = dict(
            pauta_path=self.pauta,
            inbox_path=self.inbox,
            registro_path=self.registro,
            processed_path=self.processed,
            preview=self.preview,
            today=TODAY,
        )
        kwargs.update(overrides)
        return build_local_panorama(**kwargs)

    def test_schema_and_sources_complete(self) -> None:
        panorama, completeness = self._build()
        self.assertEqual(panorama["schema_version"], PANORAMA_SCHEMA_VERSION)
        for source in ("pauta", "inbox", "registro", "inbox4mobile"):
            self.assertTrue(completeness[source]["complete"], source)
        self.assertEqual(panorama["inbox"]["count"], 3)
        self.assertEqual(panorama["registro"]["table_rows"], 7)
        self.assertEqual(panorama["faxina"]["processed_entries"], 2)
        self.assertEqual(panorama["faxina"]["processed_stale_entries"], 1)

    def test_registro_tail_is_bounded_and_recent(self) -> None:
        panorama, _ = self._build()
        tail = panorama["registro"]["tail"]
        self.assertLessEqual(len(tail), 10)
        self.assertIn("linha 7", tail[-1])

    def test_missing_pauta_fails_alone(self) -> None:
        self.pauta.unlink()
        panorama, completeness = self._build()
        self.assertFalse(completeness["pauta"]["complete"])
        self.assertEqual(completeness["pauta"]["error"], "arquivo ausente")
        self.assertTrue(completeness["inbox"]["complete"], "fallback é POR FONTE")
        self.assertEqual(panorama["pauta"]["sections"], [])
        self.assertEqual(panorama["inbox"]["count"], 3)

    def test_stale_preview_marks_inbox4mobile_incomplete(self) -> None:
        preview = {
            "status": "stale",
            "note": "índice mais velho que o Inbox4Mobile",
            "count": 1,
            "freshness": {},
            "index_present": True,
        }
        _, completeness = self._build(preview=preview)
        self.assertTrue(completeness["inbox4mobile"]["present"])
        self.assertFalse(completeness["inbox4mobile"]["complete"])
        self.assertIn("velho", completeness["inbox4mobile"]["error"])

    def test_absent_preview_is_absent(self) -> None:
        preview = {"status": "ausente", "note": "", "count": 0, "freshness": {}}
        panorama, completeness = self._build(preview=preview)
        self.assertFalse(completeness["inbox4mobile"]["present"])
        self.assertEqual(panorama["inbox4mobile"]["status"], "ausente")


if __name__ == "__main__":
    unittest.main()
