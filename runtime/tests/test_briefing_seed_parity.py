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

    def test_registro_tail_full_differential_parity(self) -> None:
        registro_text = (self.ws / "REGISTRO.md").read_text(encoding="utf-8")
        direct_tail = [
            line.rstrip() for line in registro_text.splitlines() if line.strip()
        ][-10:]
        self.assertEqual(self.panorama["registro"]["tail"], direct_tail)

    def test_faxina_signals_differential_parity(self) -> None:
        registro_text = (self.ws / "REGISTRO.md").read_text(encoding="utf-8")
        direct_rows = sum(
            1
            for line in registro_text.splitlines()
            if line.strip().startswith("|")
            and not set(line.strip()) <= {"|", "-", " ", ":"}
        ) - 1  # header
        self.assertEqual(self.panorama["faxina"]["registro_table_rows"], direct_rows)
        self.assertEqual(self.panorama["faxina"]["processed_entries"], 0)
        self.assertEqual(self.panorama["faxina"]["processed_stale_entries"], 0)

    def test_generated_for_uses_workspace_timezone(self) -> None:
        self.assertEqual(self.panorama["generated_for"], self.today.isoformat())

    def test_completeness_all_sources_ok(self) -> None:
        completeness = self.payload["payload_completeness"]
        for source in ("pauta", "inbox", "registro", "processed"):
            self.assertTrue(completeness[source]["complete"], source)


class SeedFirstTextGuard(unittest.TestCase):
    """Registro CONGELADO das menções a `PAUTA.md` no briefing-procedure.

    A #197 fechou a porta da releitura integral; este guard fecha a janela:
    linha nova mencionando `PAUTA.md` no procedure só entra atualizando o
    registro CONSCIENTEMENTE — e toda menção precisa estar qualificada
    (semente-primeiro, fallback por fonte, edição ou apresentação), nunca
    como ordem incondicional de leitura.
    """

    ALLOWED_ANCHORS = (
        "não reler `PAUTA.md`/`INBOX.md` integrais pra exibir",  # Passo 3, a regra
        "**Edição** — atualizar `PAUTA.md`/`REGISTRO.md` no fechamento",  # caso 1
        "pauta incompleta → ler `PAUTA.md`",  # caso 2, fallback por fonte
        "fallback integral — ler `PAUTA.md` e `INBOX.md` como sempre",  # sem runtime
        "arquivo `PAUTA.md` só no fallback do Passo 3",  # DAG do Passo 4
        "`Prumo/PAUTA.md` direto só no fallback do Passo 3",  # classificação
        "Pendências vivas de `PAUTA.md`",  # Passo 5, apresentação
        "no fallback, `PAUTA.md` integral",  # ponte associativa
        "Atualizar `PAUTA.md` se algo mudou",  # Passo 6, edição
        "Se `PAUTA.md` estiver vazia",  # Passo 7, brain dump
    )

    def test_every_pauta_mention_is_registered(self) -> None:
        procedure = (
            Path(__file__).resolve().parents[2]
            / "skills/prumo/references/modules/briefing-procedure.md"
        ).read_text(encoding="utf-8")
        offenders = []
        for number, line in enumerate(procedure.splitlines(), start=1):
            if "PAUTA.md" not in line:
                continue
            if not any(anchor in line for anchor in self.ALLOWED_ANCHORS):
                offenders.append(f"linha {number}: {line.strip()[:120]}")
        self.assertEqual(
            offenders,
            [],
            "menção nova a PAUTA.md no procedure sem registro no guard — "
            "a releitura integral só entra qualificada (semente/fallback/edição); "
            f"atualize ALLOWED_ANCHORS conscientemente: {offenders}",
        )

    def test_seed_first_rule_is_present(self) -> None:
        procedure = (
            Path(__file__).resolve().parents[2]
            / "skills/prumo/references/modules/briefing-procedure.md"
        ).read_text(encoding="utf-8")
        self.assertIn("semente-primeiro, #197", procedure)
        self.assertIn("prumo_local_panorama.v1", procedure)
        self.assertIn("dois casos apenas", procedure)


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

    def test_card_never_claims_clean_inbox_without_evidence(self) -> None:
        # Primeiro uso: arquivos reais no Inbox4Mobile, nenhum índice ainda.
        # O cartão NÃO pode dizer "Inbox limpa" — contagem é indeterminada.
        with tempfile.TemporaryDirectory(prefix="prumo-seed-honesto-") as tmp:
            ws, _, _ = _build_workspace(tmp)
            (ws / "INBOX.md").write_text("# Inbox\n\n_Inbox limpo._\n", encoding="utf-8")
            (ws / "Inbox4Mobile" / "captura-real.md").write_text("- algo\n", encoding="utf-8")
            payload = build_briefing_payload(ws)
            inbox_line = next(
                s["text"] for s in payload["sections"] if s["id"] == "inbox_mobile"
            )
            self.assertNotIn("Inbox limpa", inbox_line)
            self.assertIn("não inventariado", inbox_line)
            self.assertIn("prumo inbox preview", inbox_line)

    def test_corrupted_index_is_not_reported_as_gerado(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prumo-seed-corrupt-") as tmp:
            ws, _, _ = _build_workspace(tmp)
            (ws / "Inbox4Mobile" / "_preview-index.json").write_text(
                "{lixo", encoding="utf-8"
            )
            payload = build_briefing_payload(ws)
            block = payload["local_panorama"]["inbox4mobile"]
            self.assertEqual(block["status"], "invalido")
            self.assertFalse(payload["payload_completeness"]["inbox4mobile"]["complete"])

    def test_corrupted_processed_marks_source_incomplete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prumo-seed-proc-") as tmp:
            ws, _, _ = _build_workspace(tmp)
            (ws / "Inbox4Mobile" / "_processed.json").write_text("{lixo", encoding="utf-8")
            payload = build_briefing_payload(ws)
            processed = payload["payload_completeness"]["processed"]
            self.assertFalse(processed["complete"])
            self.assertIn("ilegível", processed["error"])

    def test_missing_processed_is_legitimate_and_complete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prumo-seed-noproc-") as tmp:
            ws, _, _ = _build_workspace(tmp)
            payload = build_briefing_payload(ws)
            processed = payload["payload_completeness"]["processed"]
            self.assertFalse(processed["present"])
            self.assertTrue(processed["complete"], "ausente = nada processado, não é erro")

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
