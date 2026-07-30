#!/usr/bin/env python3
"""Auditoria de execução do briefing a partir do transcript (#284).

Por que existe: em 30/07 um briefing levou 11 minutos e o dono ficou sem nada
na tela. O relato daquele dia foi artesanal — escrito uma vez, sem base de
comparação, e certificou conformidade auditando a propriedade fácil (a
numeração 1..N continuou) em vez da que importava (houve DUAS entregas?).
Este script mede sempre a mesma coisa, do mesmo jeito, para que "demorou"
vire número comparável.

**A métrica principal é `time_to_first_time`** — quanto tempo até o usuário
ver a primeira coisa útil. É a promessa da #196, e era a única que ninguém
media.

Quatro travas de desenho (revisão do Codex):

1. **Host específico, sem fingir universalidade.** O formato do transcript é
   do host e pode mudar. Campo esperado ausente → `unsupported`, nunca
   número bonito calculado sobre schema que virou outra coisa.
2. **Agregados, não conteúdo.** Saem timestamps, contagens, nomes de
   ferramenta e tokens. NUNCA prompt, texto de mensagem, corpo de email ou
   resultado de ferramenta. Transcript pessoal não vira souvenir no Git.
3. **Fase só quando observável**, e rotulada `inferida` — o erro do relatório
   de 30/07 foi transformar narrativa em medição.
4. **Sem gate de performance no CI.** O CI testa este parser contra fixtures
   sintéticas; briefing vivo depende de workspace, host e MCPs.

Uso:
    python scripts/briefing_transcript_audit.py TRANSCRIPT.jsonl [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

SCHEMA = "prumo_briefing_transcript.v1"

# Marcador de protocolo do fim do primeiro tempo (#284). Tem de ser
# byte-idêntico ao de `briefing-montagem.md` — `test_primeiro_tempo.py`
# amarra os dois. Mudar a frase exige mudar aqui, lá e no guard, no mesmo
# diff; é por isso que ela deixou de ser copy.
SENTINELA = "Curadoria de email e agenda chegando na sequência."

# Canais externos, casados pelo SUFIXO do método: o prefixo do servidor MCP é
# um UUID que muda por instalação, então casar por servidor daria falso
# negativo silencioso na máquina seguinte — que é justamente o modo de falha
# que este script existe para não repetir.
#
# É uma ALLOWLIST, e allowlist incompleta absolve em silêncio. Por isso ela
# soma os nomes que o próprio repo documenta (`briefing-canais.md`,
# `file-templates.md`, `prumo/SKILL.md`) aos padrões de família — um conector
# novo que se chame `gmail_*`/`gcal_*` é pego sem ninguém lembrar de editar
# esta lista.
EXTERNAL_SUFFIXES = frozenset(
    {
        # Gmail
        "search_threads",
        "get_thread",
        "get_message",
        "read_message",
        "list_drafts",
        "create_draft",
        "list_labels",
        "get_profile",
        # Calendar
        "list_events",
        "list_calendars",
        "search_events",
        "get_event",
        "suggest_time",
    }
)

# Famílias por nome, para o que a allowlist não previu.
EXTERNAL_PATTERNS = (
    re.compile(r"(^|_)gmail(_|$)", re.IGNORECASE),
    re.compile(r"(^|_)gcal(_|$)", re.IGNORECASE),
    re.compile(r"(^|_)google_?calendar(_|$)", re.IGNORECASE),
)

VERDICT_OK = "ok"
VERDICT_NOT_EMITTED = "first_time_not_emitted_before_external_channels"
VERDICT_MISSING = "first_time_contract_missing"
VERDICT_NOT_APPLICABLE = "not_applicable"
VERDICT_UNSUPPORTED = "unsupported"

VARIANT_TWO_TIMES = "two-times"
VARIANT_SINGLE = "single-response"


class UnsupportedTranscript(Exception):
    """O transcript não tem a forma que este parser sabe ler."""

@dataclass
class Report:
    schema: str = SCHEMA
    variant: str = VARIANT_TWO_TIMES
    verdict: str = VERDICT_OK
    reason: str = ""
    started_at: str | None = None
    first_time_at: str | None = None
    time_to_first_time_s: float | None = None
    final_at: str | None = None
    time_to_final_s: float | None = None
    first_external_at: str | None = None
    first_external_tool: str | None = None
    model_calls: int = 0
    tool_calls: int = 0
    tool_rounds: int = 0
    batched_tool_calls: int = 0
    visible_text_blocks: int = 0
    tokens: dict[str, int] = field(default_factory=dict)
    tools_by_name: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _fail(line_no: int, motivo: str) -> None:
    """Fecha o transcript como não-lido.

    Descartar um record ruim e seguir é o modo de falha que este script
    existe para não repetir: número bonito calculado sobre schema que virou
    outra coisa. Ambiguidade em record relevante = `unsupported`, com a linha.
    """
    raise UnsupportedTranscript(f"linha {line_no}: {motivo}")


def _parse_ts(raw: Any, line_no: int) -> datetime:
    if not isinstance(raw, str) or not raw:
        _fail(line_no, "timestamp ausente ou não-string")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _fail(line_no, f"timestamp não-ISO: {raw[:32]!r}")
    if parsed.tzinfo is None:
        # Ingênuo misturado com aware faz comparação estourar ou mentir.
        _fail(line_no, "timestamp sem fuso — comparação de duração seria chute")
    return parsed


def is_external_channel(name: str) -> bool:
    """Gmail/Calendar, por sufixo do método OU por família no nome."""
    if not isinstance(name, str) or not name:
        return False
    if name.rsplit("__", 1)[-1] in EXTERNAL_SUFFIXES:
        return True
    return any(p.search(name) for p in EXTERNAL_PATTERNS)


def _ends_with_sentinela(text: str) -> bool:
    """A sentinela ENCERRA o bloco — não é uma menção no meio dele.

    "Depois encerrarei com 'Curadoria de email e agenda...'" não é primeiro
    tempo, é trailer do trailer. O contrato diz "encerrado pela linha", então
    a última linha não-vazia tem de SER a linha.
    """
    linhas = [ln.strip() for ln in text.splitlines()]
    nao_vazias = [ln for ln in linhas if ln]
    if not nao_vazias:
        return False
    ultima = " ".join(nao_vazias[-1].split())
    return ultima.rstrip("*_` ").lstrip("*_`> ") == SENTINELA


def analyse(path: Path, variant: str = VARIANT_TWO_TIMES) -> Report:
    report = Report(variant=variant)
    tokens = {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}

    seq = 0
    primeiro_ts: datetime | None = None
    ultimo_ts: datetime | None = None
    first_time: tuple[int, datetime] | None = None
    first_external: tuple[int, datetime, str] | None = None
    viu_forma = False

    for line_no, record in _records(path):
        rtype = record.get("type")
        if rtype not in {"user", "assistant"}:
            continue

        sidechain = record.get("isSidechain")
        if sidechain not in (None, True, False):
            # "false" (string) é truthy e sumiria com o record inteiro.
            _fail(line_no, f"isSidechain não-booleano: {sidechain!r}")
        if sidechain:
            continue

        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if content is None:
            continue
        if not isinstance(content, list):
            _fail(line_no, "message.content presente mas não é lista")
        viu_forma = True

        ts = _parse_ts(record.get("timestamp"), line_no)
        if primeiro_ts is None:
            primeiro_ts = ts
        ultimo_ts = ts if ultimo_ts is None or ts > ultimo_ts else ultimo_ts

        if rtype == "assistant":
            report.model_calls += 1
            usage = message.get("usage")
            if isinstance(usage, dict):
                for chave, campo in (
                    ("input", "input_tokens"),
                    ("cache_creation", "cache_creation_input_tokens"),
                    ("cache_read", "cache_read_input_tokens"),
                    ("output", "output_tokens"),
                ):
                    valor = usage.get(campo, 0)
                    if valor is None:
                        valor = 0
                    if not isinstance(valor, int) or isinstance(valor, bool):
                        _fail(line_no, f"usage.{campo} não-inteiro: {valor!r}")
                    tokens[chave] += valor

        tools_na_rodada = 0
        for bloco in content:
            if not isinstance(bloco, dict):
                _fail(line_no, "bloco de content não é objeto")
            seq += 1
            btype = bloco.get("type")

            # `thinking` NÃO é entrega: é exatamente a diferença entre compor
            # e entregar que o ASSERT do core nomeia.
            if btype == "text" and rtype == "assistant":
                texto = bloco.get("text")
                if not isinstance(texto, str):
                    _fail(line_no, "bloco text sem campo text string")
                report.visible_text_blocks += 1
                if first_time is None and _ends_with_sentinela(texto):
                    first_time = (seq, ts)

            elif btype == "tool_use":
                tools_na_rodada += 1
                report.tool_calls += 1
                nome = bloco.get("name")
                if not isinstance(nome, str) or not nome:
                    _fail(line_no, "tool_use sem name string")
                report.tools_by_name[nome] = report.tools_by_name.get(nome, 0) + 1
                if first_external is None and is_external_channel(nome):
                    first_external = (seq, ts, nome)

        if tools_na_rodada:
            report.tool_rounds += 1
            # Chamadas além da primeira no mesmo turno: é o que separa
            # "agrupou" de "gastou uma rodada de modelo por ferramenta".
            report.batched_tool_calls += tools_na_rodada - 1

    if not viu_forma:
        raise UnsupportedTranscript(
            "nenhum registro com message.content em lista — schema não reconhecido"
        )

    report.tokens = tokens
    report.started_at = primeiro_ts.isoformat() if primeiro_ts else None
    report.final_at = ultimo_ts.isoformat() if ultimo_ts else None
    if first_time:
        report.first_time_at = first_time[1].isoformat()
    if first_external:
        report.first_external_at = first_external[1].isoformat()
        report.first_external_tool = first_external[2]

    if primeiro_ts and first_time:
        report.time_to_first_time_s = (first_time[1] - primeiro_ts).total_seconds()
    if primeiro_ts and ultimo_ts:
        report.time_to_final_s = (ultimo_ts - primeiro_ts).total_seconds()

    report.verdict, report.reason = _verdict(
        variant,
        first_time[0] if first_time else None,
        first_external[0] if first_external else None,
    )
    return report


def _verdict(
    variant: str, first_time_seq: int | None, first_external_seq: int | None
) -> tuple[str, str]:
    """A regra do ASSERT, na ordem CAUSAL.

    A comparação é por posição no fluxo — (record, bloco) —, nunca por
    timestamp: `tool_use` e texto do mesmo record compartilham o carimbo, e
    comparar tempo aprovaria "abriu o canal, depois escreveu" só porque os
    dois marcam o mesmo segundo.
    """
    if variant == VARIANT_SINGLE:
        return (
            VERDICT_NOT_APPLICABLE,
            "host de resposta única: o contrato de duas entregas não se aplica",
        )

    if first_time_seq is None:
        if first_external_seq is None:
            return (
                VERDICT_MISSING,
                "nenhum canal externo aberto, e o primeiro tempo nunca foi "
                "encerrado pela sentinela — em host de dois tempos ele é "
                "obrigatório mesmo sem email/agenda a consultar",
            )
        return (
            VERDICT_NOT_EMITTED,
            "canal externo aberto e a sentinela do primeiro tempo nunca "
            "apareceu em texto visível",
        )

    if first_external_seq is not None and first_external_seq < first_time_seq:
        return (
            VERDICT_NOT_EMITTED,
            "canal externo aberto antes da entrega do primeiro tempo",
        )

    return VERDICT_OK, "primeiro tempo entregue antes do primeiro canal externo"


def _records(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                _fail(line_no, f"JSON inválido ({exc.msg})")
            if not isinstance(record, dict):
                _fail(line_no, "registro não é objeto")
            yield line_no, record


def _render(report: Report) -> str:
    def secs(value: float | None) -> str:
        return "—" if value is None else f"{value:.0f}s ({value / 60:.1f} min)"

    return "\n".join(
        [
            f"veredito              {report.verdict}",
            f"  motivo              {report.reason}",
            f"  variante            {report.variant}",
            "",
            f"tempo até 1º tempo    {secs(report.time_to_first_time_s)}   <- a métrica",
            f"tempo até o fim       {secs(report.time_to_final_s)}",
            f"1º canal externo      {report.first_external_tool or '—'}",
            "",
            f"chamadas ao modelo    {report.model_calls}",
            f"chamadas de tool      {report.tool_calls} em {report.tool_rounds} rodadas",
            f"agrupadas             {report.batched_tool_calls}",
            f"blocos de texto       {report.visible_text_blocks}",
            "",
            "tokens                "
            + "  ".join(f"{k}={v:,}" for k, v in report.tokens.items()),
        ]
    )


# Veredito → código de saída. `missing` sai diferente de zero: um contrato
# chamado ausente que termina em sucesso toca sirene e entrega confete.
EXIT_CODES = {
    VERDICT_OK: 0,
    VERDICT_NOT_APPLICABLE: 0,
    VERDICT_NOT_EMITTED: 1,
    VERDICT_MISSING: 1,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--variant",
        choices=[VARIANT_TWO_TIMES, VARIANT_SINGLE],
        default=VARIANT_TWO_TIMES,
        help="variante do host (matriz do briefing-montagem.md). Cowork é "
        "two-times; o auditor não adivinha o host.",
    )
    args = parser.parse_args(argv)

    if not args.transcript.is_file():
        print(f"transcript não encontrado: {args.transcript}", file=sys.stderr)
        return 2

    try:
        report = analyse(args.transcript, variant=args.variant)
    except UnsupportedTranscript as exc:
        payload = {"schema": SCHEMA, "verdict": VERDICT_UNSUPPORTED, "reason": str(exc)}
        print(
            json.dumps(payload, ensure_ascii=False, indent=2)
            if args.json
            else f"veredito  {VERDICT_UNSUPPORTED}\n  motivo  {exc}"
        )
        return 3

    print(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2)
        if args.json
        else _render(report)
    )
    return EXIT_CODES[report.verdict]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
