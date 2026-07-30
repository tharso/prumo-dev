"""O detector do primeiro tempo (#284).

O ASSERT do core congela a regra; `test_primeiro_tempo.py` congela as peças
de texto de que ela depende. Nenhum dos dois prova que um modelo ENTREGOU
texto antes de abrir um canal — isso só é observável no transcript, e é o que
este módulo cobre.

A fixture do incidente é uma RECONSTRUÇÃO da forma descrita na linha do tempo
do relatório de 30/07 (canais externos em t+196–243 sem emissão anterior),
não uma cópia do transcript real: o conteúdo pessoal não entra no repo, e a
forma é o que importa para o detector.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SPEC = importlib.util.spec_from_file_location(
    "briefing_transcript_audit",
    REPO_ROOT / "scripts" / "briefing_transcript_audit.py",
)
assert _SPEC and _SPEC.loader
audit = importlib.util.module_from_spec(_SPEC)
sys.modules["briefing_transcript_audit"] = audit
_SPEC.loader.exec_module(audit)

MONTAGEM = (
    REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "briefing-montagem.md"
)

T0 = "2026-07-30T16:51:07.000Z"
T_LOCAL = "2026-07-30T16:54:20.000Z"
T_EXTERNO = "2026-07-30T16:54:23.000Z"
T_FIM = "2026-07-30T17:02:05.000Z"


def _assistant(ts: str, blocks: list[dict], usage: dict | None = None) -> dict:
    message: dict = {"role": "assistant", "content": blocks}
    if usage:
        message["usage"] = usage
    return {"type": "assistant", "timestamp": ts, "message": message}


def _tool(name: str) -> dict:
    return {"type": "tool_use", "name": name, "input": {}}


def _text(body: str) -> dict:
    return {"type": "text", "text": body}


def _write(records: list[dict]) -> Path:
    tmp = Path(tempfile.mkdtemp()) / "transcript.jsonl"
    tmp.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )
    return tmp


SENT = audit.SENTINELA
PRIMEIRO_TEMPO = f"Bom dia. 1. Andrea Vianna...\n\n{SENT}"


class IncidenteTest(unittest.TestCase):
    """A regressão de 30/07: onze minutos, nada na tela."""

    def test_canal_externo_antes_da_sentinela_reprova(self) -> None:
        path = _write(
            [
                _assistant(T0, [_tool("Bash")]),
                _assistant(T_LOCAL, [_tool("Read")]),
                # abre Gmail sem ter emitido nada visível
                _assistant(T_EXTERNO, [_tool("mcp__abc123__search_threads")]),
                # e só no fim entrega tudo junto, sentinela inclusa
                _assistant(T_FIM, [_text(PRIMEIRO_TEMPO + "\n\n30. Reunião 14h")]),
            ]
        )
        report = audit.analyse(path)
        self.assertEqual(report.verdict, audit.VERDICT_NOT_EMITTED)
        self.assertEqual(report.first_external_tool, "mcp__abc123__search_threads")

    def test_sentinela_so_no_bloco_final_nao_salva(self) -> None:
        # "Compor não é entregar": ter a frase na resposta final, depois de já
        # ter aberto o canal, é exatamente o que aconteceu em 30/07.
        path = _write(
            [
                _assistant(T0, [_tool("Read")]),
                _assistant(T_EXTERNO, [_tool("mcp__x__list_events")]),
                _assistant(T_FIM, [_text(PRIMEIRO_TEMPO)]),
            ]
        )
        self.assertEqual(audit.analyse(path).verdict, audit.VERDICT_NOT_EMITTED)

    def test_sentinela_em_thinking_nao_conta_como_entrega(self) -> None:
        # A brecha mais fina: o modelo "planeja" o primeiro tempo no
        # raciocínio e considera cumprido. Pensar não é entregar.
        path = _write(
            [
                _assistant(T0, [_tool("Read")]),
                _assistant(T_LOCAL, [{"type": "thinking", "thinking": PRIMEIRO_TEMPO}]),
                _assistant(T_EXTERNO, [_tool("mcp__x__search_threads")]),
                _assistant(T_FIM, [_text("pronto")]),
            ]
        )
        self.assertEqual(audit.analyse(path).verdict, audit.VERDICT_NOT_EMITTED)


class ConformeTest(unittest.TestCase):
    def test_entrega_antes_do_canal_aprova_e_mede(self) -> None:
        path = _write(
            [
                _assistant(T0, [_tool("Bash")]),
                _assistant(T_LOCAL, [_text(PRIMEIRO_TEMPO)]),
                _assistant(T_EXTERNO, [_tool("mcp__abc__search_threads")]),
                _assistant(T_FIM, [_text("2º tempo: 12. Reunião 14h")]),
            ]
        )
        report = audit.analyse(path)
        self.assertEqual(report.verdict, audit.VERDICT_OK)
        self.assertEqual(report.time_to_first_time_s, 193.0)
        self.assertEqual(report.time_to_final_s, 658.0)

    def test_sem_canal_externo_nao_e_violacao(self) -> None:
        # Briefing sem email/agenda a consultar não viola nada; só não há o
        # que provar. Reportar como falha aqui geraria alarme falso diário.
        path = _write(
            [
                _assistant(T0, [_tool("Read")]),
                _assistant(T_FIM, [_text(PRIMEIRO_TEMPO)]),
            ]
        )
        self.assertEqual(audit.analyse(path).verdict, audit.VERDICT_OK)

    def test_sem_sentinela_e_sem_canal_e_contrato_ausente(self) -> None:
        path = _write(
            [
                _assistant(T0, [_tool("Read")]),
                _assistant(T_FIM, [_text("panorama sem a linha de fechamento")]),
            ]
        )
        self.assertEqual(audit.analyse(path).verdict, audit.VERDICT_MISSING)


class ContagemTest(unittest.TestCase):
    def test_agrupamento_e_rodadas(self) -> None:
        path = _write(
            [
                # 3 ferramentas numa rodada só = 2 agrupadas
                _assistant(T0, [_tool("Read"), _tool("Read"), _tool("Read")]),
                _assistant(T_LOCAL, [_tool("Bash")]),
                _assistant(T_FIM, [_text(PRIMEIRO_TEMPO)]),
            ]
        )
        report = audit.analyse(path)
        self.assertEqual(report.tool_calls, 4)
        self.assertEqual(report.tool_rounds, 2)
        self.assertEqual(report.batched_tool_calls, 2)

    def test_subagente_nao_conta_como_entrega_nem_como_turno(self) -> None:
        path = _write(
            [
                _assistant(T0, [_tool("Read")]),
                {
                    "type": "assistant",
                    "timestamp": T_LOCAL,
                    "isSidechain": True,
                    "message": {"role": "assistant", "content": [_text(PRIMEIRO_TEMPO)]},
                },
                _assistant(T_EXTERNO, [_tool("mcp__x__search_threads")]),
                _assistant(T_FIM, [_text("fim")]),
            ]
        )
        report = audit.analyse(path)
        self.assertEqual(report.verdict, audit.VERDICT_NOT_EMITTED)
        self.assertEqual(report.model_calls, 3)

    def test_tokens_somam_as_quatro_pontas(self) -> None:
        usage = {
            "input_tokens": 10,
            "cache_creation_input_tokens": 20,
            "cache_read_input_tokens": 30,
            "output_tokens": 40,
        }
        path = _write(
            [
                _assistant(T0, [_tool("Read")], usage),
                _assistant(T_FIM, [_text(PRIMEIRO_TEMPO)], usage),
            ]
        )
        self.assertEqual(
            audit.analyse(path).tokens,
            {"input": 20, "cache_creation": 40, "cache_read": 60, "output": 80},
        )


class TravasDeDesenhoTest(unittest.TestCase):
    """As travas que o Codex pediu, verificadas em vez de prometidas."""

    def test_schema_desconhecido_nao_vira_numero_bonito(self) -> None:
        path = _write([{"type": "assistant", "timestamp": T0, "message": "texto cru"}])
        with self.assertRaises(audit.UnsupportedTranscript):
            audit.analyse(path)

    def test_relatorio_nao_vaza_conteudo(self) -> None:
        # Trava 2: agregados, não conteúdo. Se algum campo do relatório
        # carregar texto de mensagem, o transcript pessoal vira souvenir.
        segredo = "Andrea Vianna proposta ajustada 01:27"
        path = _write(
            [
                _assistant(T0, [_tool("Read")]),
                _assistant(T_LOCAL, [_text(f"{segredo}\n\n{SENT}")]),
                _assistant(T_FIM, [_text(segredo)]),
            ]
        )
        despejo = json.dumps(audit.analyse(path).as_dict(), ensure_ascii=False)
        self.assertNotIn("Andrea", despejo)
        self.assertNotIn("proposta", despejo)

    def test_sentinela_do_parser_bate_com_o_contrato(self) -> None:
        # A relação, não o ingrediente: duas grafias divergentes fariam o
        # parser procurar uma frase que o produto nunca emite — detector
        # cenográfico, sempre reprovando ou sempre aprovando.
        self.assertIn(audit.SENTINELA, MONTAGEM.read_text(encoding="utf-8"))

    def test_canal_externo_casa_por_sufixo_nao_por_servidor(self) -> None:
        # O prefixo do MCP é UUID por instalação; casar por servidor daria
        # falso negativo silencioso na máquina seguinte.
        for nome in (
            "mcp__aadaeb5f-ed71-4732-91d7-16cc31a08852__search_threads",
            "mcp__8bb898a7-0f09-4a14-8b2e-e2f569eca932__list_events",
            "mcp__QUALQUER_OUTRO_UUID__get_message",
        ):
            path = _write(
                [
                    _assistant(T0, [_tool("Read")]),
                    _assistant(T_EXTERNO, [_tool(nome)]),
                    _assistant(T_FIM, [_text(PRIMEIRO_TEMPO)]),
                ]
            )
            self.assertEqual(
                audit.analyse(path).verdict,
                audit.VERDICT_NOT_EMITTED,
                f"{nome} não foi reconhecido como canal externo",
            )

    def test_ferramenta_local_nao_e_canal_externo(self) -> None:
        # Ler arquivo, rodar shell e buscar versão pertencem ao primeiro
        # tempo. O preflight (WebFetch) fica fora por construção.
        for nome in ("Read", "Bash", "WebFetch", "Grep"):
            path = _write(
                [
                    _assistant(T0, [_tool(nome)]),
                    _assistant(T_FIM, [_text(PRIMEIRO_TEMPO)]),
                ]
            )
            self.assertEqual(audit.analyse(path).verdict, audit.VERDICT_OK, nome)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
