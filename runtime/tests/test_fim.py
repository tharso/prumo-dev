"""Detector de acúmulo do `/fim` (#126).

Trava: sinais determinísticos, sugestões corretas, read-only, e a cerca contra
overlap com o briefing (não toca `last-briefing.json`, não lê email/calendário).
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


class FimDetectorTests(unittest.TestCase):
    def _accumulated_ws(self, root: Path) -> Path:
        (root / "_state" / "decidir").mkdir(parents=True, exist_ok=True)
        (root / "backups").mkdir(parents=True, exist_ok=True)
        (root / "PAUTA.md").write_text(
            "# Pauta\n\n## Quente\n- [X] coisa parada (desde 01/03)\n- [Y] coisa nova (desde 20/06)\n",
            encoding="utf-8",
        )
        (root / "INBOX.md").write_text("# Inbox\n\n- triar isso\n- e aquilo\n", encoding="utf-8")
        (root / "REGISTRO.md").write_text(
            "# Registro\n\n| Data | Origem | Resumo | Acao | Destino |\n|---|---|---|---|---|\n| 01/06 | PAUTA | x | Concluido | REGISTRO |\n",
            encoding="utf-8",
        )
        (root / "last-briefing.json").write_text('{"at": "2026-06-26T09:00:00"}', encoding="utf-8")
        old_backup = root / "backups" / "velho.tar"
        old_backup.write_text("x", encoding="utf-8")
        os.utime(old_backup, (OLD_TS, OLD_TS))
        old_html = root / "_state" / "decidir" / "antigo.html"
        old_html.write_text("<html></html>", encoding="utf-8")
        os.utime(old_html, (OLD_TS, OLD_TS))
        return root

    def test_detects_accumulation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._accumulated_ws(Path(tmp))
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["schema_version"], SCHEMA_VERSION)
            s = result["signals"]
            self.assertEqual(s["pauta_stalled"], 1)   # só o "desde 01/03"
            self.assertEqual(s["inbox_pending"], 2)
            self.assertEqual(s["registro_rows"], 1)
            self.assertEqual(s["backups_old"], 1)
            self.assertEqual(s["ephemeral_html_old"], 1)
            self.assertTrue(result["suggest"]["higiene"])
            self.assertTrue(result["suggest"]["sanitize"])

    def test_clean_workspace_no_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "_state").mkdir(parents=True, exist_ok=True)
            (ws / "PAUTA.md").write_text("# Pauta\n\n## Quente\n- [Y] nova (desde 25/06)\n", encoding="utf-8")
            (ws / "INBOX.md").write_text("# Inbox\n\n_Inbox limpo._\n", encoding="utf-8")
            (ws / "REGISTRO.md").write_text("# Registro\n", encoding="utf-8")
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["signals"]["pauta_stalled"], 0)
            self.assertEqual(result["signals"]["inbox_pending"], 0)
            self.assertFalse(result["suggest"]["higiene"])
            self.assertFalse(result["suggest"]["sanitize"])

    def test_counts_legacy_backup_dir(self) -> None:
        # Regressão do #8 do Codex: a sanitize cuida de .prumo/backups E do
        # legado .prumo/backup; o detector tem que contar os dois.
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "_state").mkdir(parents=True, exist_ok=True)
            (ws / "backup").mkdir(parents=True, exist_ok=True)  # legado (flat: system_root == root)
            (ws / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
            old = ws / "backup" / "antigo.tar"
            old.write_text("x", encoding="utf-8")
            os.utime(old, (OLD_TS, OLD_TS))
            result = accumulation_signals(ws, today=TODAY)
            self.assertEqual(result["signals"]["backups_old"], 1)
            self.assertTrue(result["suggest"]["sanitize"])

    def test_read_only_and_does_not_touch_last_briefing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._accumulated_ws(Path(tmp))
            lb = ws / "last-briefing.json"
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
            (ws / "_state").mkdir(parents=True, exist_ok=True)
            (ws / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["fim", "--workspace", str(ws), "--format", "json"])
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
            self.assertIn("suggest", payload)


if __name__ == "__main__":
    unittest.main()
