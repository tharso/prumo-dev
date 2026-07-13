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
VERSION_UPDATE = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "version-update.md"


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
        # Coerência do anti-nag (review Codex r2): "não re-oferecer na sessão"
        # não pode engolir a cobrança do /fim — que acontece NA sessão. O
        # contrato certo distingue os dois momentos:
        self.assertIn("não repetir a oferta antes do `/fim`", text)
        self.assertIn("no `/fim`, cobrar uma vez", text)
        self.assertIn("recusa explícita", text)
        self.assertIn("suggest.update", text)
        # r3: a oferta-modelo expõe as TRÊS opções do canônico (um agente que
        # copia o exemplo não pode esconder o `c`).
        self.assertIn("ver diagnóstico", text)

    def test_version_update_e_o_canonico_do_protocolo(self) -> None:
        # r2 do Codex: o protocolo duplicado divergiu uma vez; agora o
        # version-update.md é o canônico e carrega a semântica completa.
        text = self._flat(VERSION_UPDATE)
        self.assertIn("canônica", text)
        self.assertIn("adiamento", text)
        self.assertIn("recusa explícita", text)
        # O `c) ver diagnóstico` tem contrato: não suspende nem conta como
        # adiamento/recusa (era a terceira opção sem semântica).
        self.assertIn("sem suspender o fluxo", text)
        self.assertIn("não é adiamento nem recusa", text)
        # r4: gatilho GRADUADO alinhado ao briefing — sem ele, o canônico
        # mandava oferecer a cada patch (nag) e contradizia o warning/alert.
        self.assertIn("gatilho graduado", text)
        self.assertIn("aviso de uma linha", text)
        # r5: a tabela de severidades também aponta a OFERTA (não "aviso") em
        # warning/alert — era o resquício que contradizia o Passo 4.
        self.assertIn("`warning` — **1 minor atrás** → **oferta no topo**".lower(), text)

    def test_fim_cobra_update_na_saida(self) -> None:
        text = self._flat(FIM_SKILL)
        self.assertIn("suggest.update", text)
        # As três situações: adiou → cobra; recusou → silêncio; compactação → fallback.
        # r3: silêncio no briefing TAMBÉM é adiamento (a enumeração não pode
        # ser lida como exaustiva sem ele — o /fim deixaria de cobrar).
        self.assertIn("silêncio", text)
        # r4: pedir o diagnóstico (c) e não decidir também é adiamento — sem
        # isso, o c vira rota de fuga que o /fim nunca cobra.
        self.assertIn("não decidiu", text)
        self.assertIn("adiou", text)
        self.assertIn("recusou explicitamente", text)
        self.assertIn("sob compactação", text)
        # Composição com o acúmulo (r2): momentos distintos, update por último,
        # e a pergunta não carrega nome de comando.
        self.assertIn("última pergunta", text)
        self.assertIn("nunca duas perguntas", text)
        self.assertIn("quer que eu atualize", text)
        self.assertNotIn("rodo o `prumo update`", text)

    def test_fim_textual_nao_faz_rede_nem_escreve_cache(self) -> None:
        # O banner de versão (check_and_notify) faz fetch + escrita de cache;
        # o `prumo fim` TEXTUAL passaria por ele sem esta supressão (review
        # Codex) — quebrando a promessa read-only/sem-rede do /fim.
        from prumo_runtime.version_check import SUPPRESS_COMMANDS

        self.assertIn("fim", SUPPRESS_COMMANDS)


if __name__ == "__main__":
    unittest.main()
