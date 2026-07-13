"""Update pendente: de aviso a oferta (#174).

Report do dono: o briefing detectou versão nova e "deixou pra depois"; o /fim
ignorou. Travas: (a) o detector do /fim ganha o sinal `update_pending` (cache,
sem rede nova); (b) o briefing-procedure manda ABRIR com a oferta (escolha
curta, não-bloqueante, anti-nag); (c) o /fim cobra na saída.
"""
from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from prumo_runtime.fim import accumulation_signals

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIEFING_PROC = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "briefing-procedure.md"
FIM_SKILL = REPO_ROOT / "skills" / "fim" / "SKILL.md"


def _ws(root: Path, core_version: str | None) -> Path:
    (root / "Prumo").mkdir(parents=True, exist_ok=True)
    (root / "Prumo" / "PAUTA.md").write_text("# Pauta\n\n## Quente\n", encoding="utf-8")
    (root / "Prumo" / "INBOX.md").write_text("# Inbox\n", encoding="utf-8")
    (root / "Prumo" / "REGISTRO.md").write_text("# Registro\n", encoding="utf-8")
    if core_version:
        sysdir = root / ".prumo" / "system"
        sysdir.mkdir(parents=True, exist_ok=True)
        (sysdir / "PRUMO-CORE.md").write_text(
            f"> **prumo_version: {core_version}**\n", encoding="utf-8"
        )
    return root


class UpdatePendingSignal(unittest.TestCase):
    def test_core_atras_da_publica_sugere_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _ws(Path(tmp), "5.30.0")
            with mock.patch(
                "prumo_runtime.fim.read_cached_remote_version", return_value="5.33.0"
            ):
                result = accumulation_signals(ws)
        self.assertTrue(result["suggest"]["update"])
        self.assertEqual(result["signals"]["installed_version"], "5.30.0")
        self.assertEqual(result["signals"]["remote_version"], "5.33.0")

    def test_sem_cache_nao_sugere(self) -> None:
        # Sem cache remoto → não inventa urgência (fail-open silencioso).
        with tempfile.TemporaryDirectory() as tmp:
            ws = _ws(Path(tmp), "5.30.0")
            with mock.patch(
                "prumo_runtime.fim.read_cached_remote_version", return_value=None
            ):
                result = accumulation_signals(ws)
        self.assertFalse(result["suggest"]["update"])

    def test_core_em_dia_nao_sugere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _ws(Path(tmp), "5.33.0")
            with mock.patch(
                "prumo_runtime.fim.read_cached_remote_version", return_value="5.33.0"
            ):
                result = accumulation_signals(ws)
        self.assertFalse(result["suggest"]["update"])

    def test_render_texto_menciona_update_pendente(self) -> None:
        from prumo_runtime.commands.fim import _render_text

        with tempfile.TemporaryDirectory() as tmp:
            ws = _ws(Path(tmp), "5.30.0")
            with mock.patch(
                "prumo_runtime.fim.read_cached_remote_version", return_value="5.33.0"
            ):
                result = accumulation_signals(ws)
        text = _render_text(result)
        self.assertIn("5.30.0", text)
        self.assertIn("5.33.0", text)
        self.assertIn("pendente", text.lower())


class SkillContractGuards(unittest.TestCase):
    def _flat(self, path: Path) -> str:
        return " ".join(path.read_text(encoding="utf-8").lower().split())

    def test_briefing_abre_com_oferta_executavel(self) -> None:
        text = self._flat(BRIEFING_PROC)
        # A oferta explícita, com ORDEM executável: abre a resposta e o
        # briefing segue na MESMA resposta (não espera → não-bloqueante real).
        self.assertIn("atualizar agora", text)
        self.assertIn("na mesma resposta", text)
        self.assertIn("não-bloqueante", text)
        # Semântica sem ambiguidade (review Codex): adiar ≠ recusar.
        self.assertIn("adiamento", text)
        self.assertIn("recusa explícita", text)
        # Anti-nag e quem cobra depois (nome real do campo do payload).
        self.assertIn("nunca re-oferecer", text)
        self.assertIn("suggest.update", text)

    def test_fim_cobra_update_na_saida(self) -> None:
        text = self._flat(FIM_SKILL)
        self.assertIn("suggest.update", text)
        # As três situações: adiou → cobra; recusou → silêncio; compactação → fallback.
        self.assertIn("adiou", text)
        self.assertIn("recusou explicitamente", text)
        self.assertIn("sob compactação", text)

    def test_fim_textual_nao_faz_rede_nem_escreve_cache(self) -> None:
        # O banner de versão (check_and_notify) faz fetch + escrita de cache;
        # o `prumo fim` TEXTUAL passaria por ele sem esta supressão (review
        # Codex) — quebrando a promessa read-only/sem-rede do /fim.
        from prumo_runtime.version_check import SUPPRESS_COMMANDS

        self.assertIn("fim", SUPPRESS_COMMANDS)


if __name__ == "__main__":
    unittest.main()
