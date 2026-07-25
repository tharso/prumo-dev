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

## Horizonte (importante mas não urgente)

- Ideia de longo prazo
- Outra aposta | cobrar: 30/12

## Agendado Futuro

- Compromisso de setembro

## Notas do sistema

- Configuração X vale Y
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

    def test_non_canonical_sections_are_transported(self) -> None:
        # #206: a PAUTA real tem seções autorais — não podem sumir na semente.
        outras = {s["label"]: s for s in self.block["outras_secoes"]}
        self.assertEqual(
            list(outras),
            ["Horizonte (importante mas não urgente)", "Agendado Futuro", "Notas do sistema"],
            "todas as seções não-canônicas, na ordem do arquivo",
        )
        self.assertEqual(outras["Horizonte (importante mas não urgente)"]["count"], 2)
        self.assertEqual(outras["Agendado Futuro"]["count"], 1)

    def test_canonical_sections_never_duplicate_into_outras(self) -> None:
        # "Quente" (com sufixo visual ou sem) casa com a canônica → fora de outras.
        outras_labels = [s["label"] for s in self.block["outras_secoes"]]
        for label in outras_labels:
            self.assertNotIn("Quente", label)
            self.assertNotIn("Hibernando", label)

    def test_agendado_futuro_is_not_swallowed_by_agendado(self) -> None:
        # O matcher estrito rejeita "Agendado Futuro" como "Agendado" (a letra
        # F não é separador) — tem que vir em outras_secoes, não sumir.
        self.assertEqual(self.by_id["agendado"]["count"], 1, "só o Agendado 1")
        outras = {s["label"] for s in self.block["outras_secoes"]}
        self.assertIn("Agendado Futuro", outras)

    def test_total_item_count_parity_with_direct_reading(self) -> None:
        # Guard da #206: NADA se perde — soma da semente == leitura direta.
        from prumo_runtime.pauta_parsing import extract_all_sections

        direct_total = sum(len(items) for _, items in extract_all_sections(PAUTA))
        seed_total = sum(s["count"] for s in self.block["sections"]) + sum(
            s["count"] for s in self.block["outras_secoes"]
        )
        self.assertEqual(seed_total, direct_total)

    def test_outras_items_carry_cobrar_and_budget_fields(self) -> None:
        outras = {s["label"]: s for s in self.block["outras_secoes"]}
        aposta = outras["Horizonte (importante mas não urgente)"]["items"][1]
        self.assertIn("cobrar", aposta)
        self.assertEqual(aposta["cobrar"]["state"], "future")
        self.assertFalse(aposta["visible_today"])


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
