"""Detector de acúmulo do `/fim` (#126).

Trava: sinais determinísticos em layout NESTED real (infra em `.prumo/`, dados em
`Prumo/`), sugestões corretas, read-only, e a cerca contra overlap com o briefing
(não toca `last-briefing.json`, não lê email/calendário).
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

from prumo_runtime.fim import SCHEMA_VERSION, accumulation_signals

TODAY = date(2026, 6, 26)
OLD_TS = time.mktime(date(2026, 3, 1).timetuple())  # ~117 dias antes de TODAY


def _snapshot(root: Path) -> dict[str, float]:
    return {str(p): p.stat().st_mtime for p in root.rglob("*") if p.is_file()}


def _old(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.utime(path, (OLD_TS, OLD_TS))
    return path


class FimDetectorTests(unittest.TestCase):
    def _accumulated_ws(self, root: Path) -> Path:
        # Layout NESTED real: dados em Prumo/, infra hardcoded em .prumo/.
        (root / "Prumo").mkdir(parents=True, exist_ok=True)
        (root / ".prumo" / "state").mkdir(parents=True, exist_ok=True)
        (root / "Prumo" / "PAUTA.md").write_text(
            "# Pauta\n\n## Quente\n"
            "- [Trabalho] coisa parada (desde 01/03)\n"
            "- [Pessoal] coisa nova (desde 20/06)\n"
            "- [x] tarefa concluida (desde 01/01)\n",  # concluída → não conta
            encoding="utf-8",
        )
        (root / "Prumo" / "INBOX.md").write_text("# Inbox\n\n- triar isso\n- e aquilo\n", encoding="utf-8")
        (root / "Prumo" / "REGISTRO.md").write_text(
            "# Registro\n\n| Data | Origem | Resumo | Acao | Destino |\n|---|---|---|---|---|\n"
            "| 01/06 | PAUTA | x | Concluido | REGISTRO |\n",
            encoding="utf-8",
        )
        (root / ".prumo" / "state" / "last-briefing.json").write_text(
            '{"at": "2026-06-26T09:00:00"}', encoding="utf-8"
        )
        _old(root / ".prumo" / "backups" / "velho.tar")
        _old(root / ".prumo" / "state" / "decidir" / "antigo.html", "<html></html>")
        return root

    def test_detects_accumulation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._accumulated_ws(Path(tmp))
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["schema_version"], SCHEMA_VERSION)
            s = result["signals"]
            self.assertEqual(s["pauta_stalled"], 1)   # só "desde 01/03" (nova é recente; [x] pulado)
            self.assertEqual(s["inbox_pending"], 2)
            self.assertEqual(s["registro_rows"], 1)
            self.assertEqual(s["backups_old"], 1)
            self.assertEqual(s["ephemeral_old"], 1)
            self.assertTrue(result["suggest"]["higiene"])
            self.assertTrue(result["suggest"]["sanitize"])

    def test_done_checkbox_not_counted_as_stalled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo" / "PAUTA.md").write_text(
                "# Pauta\n\n- [x] feito ha tempao (desde 01/01)\n- [X] outro feito (desde 01/02)\n",
                encoding="utf-8",
            )
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["signals"]["pauta_stalled"], 0)

    def test_desde_29_02_resolves_to_prior_leap_year(self) -> None:
        # Regressão: `desde 29/02` sem ano, com hoje em ano não-bissexto (2026),
        # tem que cair em 2024 (último 29/02 válido ≤ hoje), não virar falso negativo.
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo" / "PAUTA.md").write_text(
                "# Pauta\n\n- [Trabalho] item antigo (desde 29/02)\n", encoding="utf-8"
            )
            # trava o ANO exato, não só o efeito: 2024 (último 29/02 ≤ 2026-06-26)
            from prumo_runtime.fim import _DESDE_PATTERN, _parse_desde
            self.assertEqual(_parse_desde(_DESDE_PATTERN.search("desde 29/02"), TODAY), date(2024, 2, 29))
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["signals"]["pauta_stalled"], 1)

    def test_clean_workspace_no_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo" / "PAUTA.md").write_text(
                "# Pauta\n\n## Quente\n- [Pessoal] nova (desde 25/06)\n", encoding="utf-8"
            )
            (ws / "Prumo" / "INBOX.md").write_text("# Inbox\n\n_Inbox limpo._\n", encoding="utf-8")
            (ws / "Prumo" / "REGISTRO.md").write_text("# Registro\n", encoding="utf-8")
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["signals"]["pauta_stalled"], 0)
            self.assertEqual(result["signals"]["inbox_pending"], 0)
            self.assertFalse(result["suggest"]["higiene"])
            self.assertFalse(result["suggest"]["sanitize"])

    def test_counts_legacy_backup_dir(self) -> None:
        # Regressão do #8 do Codex: a sanitize cuida de .prumo/backups E do legado
        # .prumo/backup; o detector conta os dois (sempre sob .prumo/).
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "Prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo" / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
            _old(ws / ".prumo" / "backup" / "antigo.tar")  # legado
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["signals"]["backups_old"], 1)
            self.assertTrue(result["suggest"]["sanitize"])

    def test_ephemeral_counts_nonhtml_font(self) -> None:
        # Regressão: a Boliand.otf efêmera (não-.html) também é lixo que a sanitize
        # limpa; o detector tem que contá-la.
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "Prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo" / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
            _old(ws / ".prumo" / "state" / "acervo" / "Boliand.otf", "fontbytes")
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["signals"]["ephemeral_old"], 1)
            self.assertTrue(result["suggest"]["sanitize"])

    def test_read_only_and_does_not_touch_last_briefing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._accumulated_ws(Path(tmp))
            lb = ws / ".prumo" / "state" / "last-briefing.json"
            lb_before = lb.read_text(encoding="utf-8")
            before = _snapshot(ws)
            accumulation_signals(ws, today=TODAY)
            self.assertEqual(_snapshot(ws), before, "detector não pode escrever nada")
            self.assertEqual(lb.read_text(encoding="utf-8"), lb_before, "não pode tocar last-briefing.json")


class FimCliTests(unittest.TestCase):
    def test_cli_fim_json(self) -> None:
        import io
        import json
        from contextlib import redirect_stdout

        from prumo_runtime.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo").mkdir(parents=True, exist_ok=True)
            (ws / "Prumo" / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["fim", "--workspace", str(ws), "--format", "json"])
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
            self.assertIn("suggest", payload)


if __name__ == "__main__":
    unittest.main()
