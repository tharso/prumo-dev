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
EXTERNAL_SUFFIXES = frozenset(
    {
        # Gmail
        "search_threads",
        "get_thread",
        "get_message",
        "list_drafts",
        "create_draft",
        "list_labels",
        # Calendar
        "list_events",
        "list_calendars",
        "search_events",
        "get_event",
        "suggest_time",
    }
)

VERDICT_OK = "ok"
VERDICT_NOT_EMITTED = "first_time_not_emitted_before_external_channels"
VERDICT_MISSING = "first_time_contract_missing"
VERDICT_UNSUPPORTED = "unsupported"


class UnsupportedTranscript(Exception):
    """O transcript não tem a forma que este parser sabe ler."""


@dataclass
class Report:
    schema: str = SCHEMA
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
        return {k: v for k, v in self.__dict__.items()}


def _parse_ts(raw: str | None) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def _blocks(record: dict[str, Any]) -> list[dict[str, Any]]:
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict)]


def _tool_suffix(name: str) -> str:
    return name.rsplit("__", 1)[-1] if name else ""


def analyse(path: Path) -> Report:
    report = Report()
    seen_shape = False
    tokens = {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}

    first_ts: datetime | None = None
    first_time_ts: datetime | None = None
    last_ts: datetime | None = None
    first_external_ts: datetime | None = None

    for record in _records(path):
        rtype = record.get("type")
        if rtype not in {"user", "assistant"}:
            continue
        ts = _parse_ts(record.get("timestamp"))
        blocks = _blocks(record)
        if blocks:
            seen_shape = True

        # Subagente não é entrega ao usuário nem turno do laço principal.
        if record.get("isSidechain"):
            continue

        if rtype == "assistant":
            report.model_calls += 1
            message = record.get("message")
            usage = message.get("usage") if isinstance(message, dict) else None
            if isinstance(usage, dict):
                tokens["input"] += int(usage.get("input_tokens") or 0)
                tokens["cache_creation"] += int(
                    usage.get("cache_creation_input_tokens") or 0
                )
                tokens["cache_read"] += int(usage.get("cache_read_input_tokens") or 0)
                tokens["output"] += int(usage.get("output_tokens") or 0)

        round_tools = 0
        for block in blocks:
            btype = block.get("type")

            # `thinking` NÃO é entrega: é exatamente a diferença entre compor
            # e entregar que o ASSERT do core nomeia.
            if btype == "text" and rtype == "assistant":
                report.visible_text_blocks += 1
                text = block.get("text") or ""
                if first_time_ts is None and SENTINELA in text:
                    first_time_ts = ts
                if ts and (last_ts is None or ts > last_ts):
                    last_ts = ts

            elif btype == "tool_use":
                round_tools += 1
                report.tool_calls += 1
                name = block.get("name") or ""
                report.tools_by_name[name] = report.tools_by_name.get(name, 0) + 1
                if first_ts is None and ts:
                    first_ts = ts
                if _tool_suffix(name) in EXTERNAL_SUFFIXES and first_external_ts is None:
                    first_external_ts = ts
                    report.first_external_tool = name

        if round_tools:
            report.tool_rounds += 1
            # Chamadas além da primeira no mesmo turno: é o que separa
            # "agrupou" de "gastou uma rodada de modelo por ferramenta".
            report.batched_tool_calls += round_tools - 1

    if not seen_shape:
        raise UnsupportedTranscript(
            "nenhum registro com message.content em lista — schema não reconhecido"
        )

    report.tokens = tokens
    report.started_at = first_ts.isoformat() if first_ts else None
    report.first_time_at = first_time_ts.isoformat() if first_time_ts else None
    report.final_at = last_ts.isoformat() if last_ts else None
    report.first_external_at = (
        first_external_ts.isoformat() if first_external_ts else None
    )

    if first_ts and first_time_ts:
        report.time_to_first_time_s = (first_time_ts - first_ts).total_seconds()
    if first_ts and last_ts:
        report.time_to_final_s = (last_ts - first_ts).total_seconds()

    report.verdict, report.reason = _verdict(first_time_ts, first_external_ts)
    return report


def _verdict(
    first_time_ts: datetime | None, first_external_ts: datetime | None
) -> tuple[str, str]:
    """A regra do ASSERT, na forma observável.

    A ausência da sentinela é reportada de dois jeitos diferentes de
    propósito: sem canal externo, o briefing pode simplesmente não ter tido
    email/agenda a consultar (não é violação); COM canal externo aberto e sem
    sentinela antes, é a falha de 30/07.
    """
    if first_external_ts is None:
        if first_time_ts is None:
            return VERDICT_MISSING, "sentinela ausente e nenhum canal externo aberto"
        return VERDICT_OK, "primeiro tempo entregue; nenhum canal externo aberto"

    if first_time_ts is None:
        return (
            VERDICT_NOT_EMITTED,
            "canal externo aberto e a sentinela do primeiro tempo nunca "
            "apareceu em texto visível",
        )

    if first_external_ts < first_time_ts:
        return (
            VERDICT_NOT_EMITTED,
            "canal externo aberto antes da entrega do primeiro tempo",
        )

    return VERDICT_OK, "primeiro tempo entregue antes do primeiro canal externo"


def _render(report: Report) -> str:
    def secs(value: float | None) -> str:
        if value is None:
            return "—"
        return f"{value:.0f}s ({value / 60:.1f} min)"

    lines = [
        f"veredito              {report.verdict}",
        f"  motivo              {report.reason}",
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
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.transcript.is_file():
        print(f"transcript não encontrado: {args.transcript}", file=sys.stderr)
        return 2

    try:
        report = analyse(args.transcript)
    except UnsupportedTranscript as exc:
        payload = {"schema": SCHEMA, "verdict": VERDICT_UNSUPPORTED, "reason": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else
              f"veredito  {VERDICT_UNSUPPORTED}\n  motivo  {exc}")
        return 3

    print(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2)
        if args.json
        else _render(report)
    )
    return 1 if report.verdict == VERDICT_NOT_EMITTED else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
