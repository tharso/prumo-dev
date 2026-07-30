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
    unclassified_mcp_before_first_time: list[str] = field(default_factory=list)

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


_BLOCKQUOTE = re.compile(r"^\s*>")
_CODESPAN = re.compile(r"^\s*`[^`]*`\s*$")


def _strip_enfase(linha: str) -> str:
    """Tira ênfase Markdown e aspas em volta do payload.

    O contrato exibe a frase entre aspas e itálico (`briefing-montagem.md:25`),
    então rejeitá-las seria rígido demais. Blockquote e code span, não: eles
    MUDAM a função semântica da linha — citar a regra não é cumpri-la.
    """
    texto = linha.strip()
    for _ in range(4):
        anterior = texto
        texto = texto.strip()
        for par in ('""', "''", "**", "__", "*", "_", "“”", "‘’"):
            abre, fecha = par[0], par[-1]
            if len(texto) > 1 and texto.startswith(abre) and texto.endswith(fecha):
                texto = texto[1:-1]
        if texto == anterior:
            break
    return " ".join(texto.split())


def _encerra_com_sentinela(texto: str) -> bool:
    """A sentinela ENCERRA o bloco — não é menção no meio nem citação."""
    nao_vazias = [ln for ln in texto.splitlines() if ln.strip()]
    if not nao_vazias:
        return False
    ultima = nao_vazias[-1]
    if _BLOCKQUOTE.match(ultima) or _CODESPAN.match(ultima):
        return False
    return _strip_enfase(ultima) == SENTINELA


_MCP = re.compile(r"^mcp__(?P<servidor>[^_]+(?:_[^_]+)*)__(?P<metodo>.+)$")


def _mcp_opaco(nome: str) -> bool:
    """Ferramenta MCP cujo servidor não se identifica no nome.

    O prefixo é UUID por instalação, então `mcp__<uuid>__get_attachment` pode
    ser Gmail e a allowlist não sabe. Não dá para reprovar por isso — Slack,
    Granola e afins são MCP legítimo no meio do briefing. O que NÃO dá é
    certificar `ok` tendo visto chamadas assim antes da entrega: absolver por
    omissão é o modo de falha que este script existe para não repetir.
    """
    m = _MCP.match(nome)
    if not m:
        return False
    servidor = m.group("servidor")
    # Servidor legível (slack, supabase, vercel...) não é opaco.
    return bool(re.fullmatch(r"[0-9a-f]{6,}(-[0-9a-f]+)*", servidor, re.IGNORECASE))


@dataclass
class _Entrega:
    """Um record de assistente = UMA entrega ao usuário."""

    idx: int
    ts: datetime
    encerra_com_sentinela: bool = False
    tem_canal_externo: bool = False
    canal: str | None = None
    opacos: list[str] = field(default_factory=list)


def analyse(
    path: Path, variant: str = VARIANT_TWO_TIMES, since: datetime | None = None
) -> Report:
    report = Report(variant=variant)
    tokens = {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
    entregas: list[_Entrega] = []
    carimbos: list[datetime] = []
    viu_forma = False
    idx = 0

    for line_no, record in _records(path):
        rtype = record.get("type")
        if rtype not in {"user", "assistant"}:
            continue

        sidechain = record.get("isSidechain")
        if sidechain not in (None, True, False):
            _fail(line_no, f"isSidechain não-booleano: {sidechain!r}")
        if sidechain:
            continue

        message = record.get("message")
        content = message.get("content") if isinstance(message, dict) else None

        # Fail-closed vale para o ASSISTENTE, onde mora toda a evidência do
        # veredito. Records de `user` variam de forma entre versões do host e
        # não decidem nada aqui — exigir deles quebraria o auditor em
        # transcript legítimo sem ganhar precisão.
        if rtype == "assistant":
            if not isinstance(message, dict):
                _fail(line_no, "record de assistente sem message objeto")
            if not isinstance(content, list):
                _fail(line_no, "message.content de assistente não é lista")
        elif not isinstance(content, list):
            continue

        viu_forma = True
        ts = _parse_ts(record.get("timestamp"), line_no)
        if since is not None and ts < since:
            continue
        carimbos.append(ts)
        idx += 1

        if rtype == "assistant":
            report.model_calls += 1
            usage = message.get("usage")
            if usage is not None and not isinstance(usage, dict):
                _fail(line_no, f"usage presente mas não é objeto: {type(usage).__name__}")
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

        entrega = _Entrega(idx=idx, ts=ts)
        textos: list[str] = []
        tools_na_rodada = 0

        for bloco in content:
            if not isinstance(bloco, dict):
                _fail(line_no, "bloco de content não é objeto")
            btype = bloco.get("type")

            if btype == "text" and rtype == "assistant":
                texto = bloco.get("text")
                if not isinstance(texto, str):
                    _fail(line_no, "bloco text sem campo text string")
                report.visible_text_blocks += 1
                textos.append(texto)

            elif btype == "tool_use":
                tools_na_rodada += 1
                report.tool_calls += 1
                nome = bloco.get("name")
                if not isinstance(nome, str) or not nome:
                    _fail(line_no, "tool_use sem name string")
                report.tools_by_name[nome] = report.tools_by_name.get(nome, 0) + 1
                if is_external_channel(nome):
                    if not entrega.tem_canal_externo:
                        entrega.tem_canal_externo = True
                        entrega.canal = nome
                elif _mcp_opaco(nome):
                    entrega.opacos.append(nome)

        # A sentinela encerra a ENTREGA, não um bloco qualquer dela: com
        # [text(...sentinela), text("e já adianto...")] a frase não fecha
        # coisa nenhuma.
        if textos and _encerra_com_sentinela(textos[-1]):
            entrega.encerra_com_sentinela = True

        if tools_na_rodada:
            report.tool_rounds += 1
            report.batched_tool_calls += tools_na_rodada - 1

        entregas.append(entrega)

    if not viu_forma:
        raise UnsupportedTranscript(
            "nenhum registro com message.content em lista — schema não reconhecido"
        )

    # Uma entrega que fecha o primeiro tempo E abre canal na mesma mensagem
    # não é primeiro tempo: é o bloco único que a #284 revogou.
    primeiras = [e for e in entregas if e.encerra_com_sentinela and not e.tem_canal_externo]
    if len(primeiras) > 1 and since is None:
        raise UnsupportedTranscript(
            f"{len(primeiras)} primeiros tempos no mesmo arquivo — o transcript "
            "cobre mais de um briefing; delimite com --since, senão a sentinela "
            "de ontem absolve a violação de hoje"
        )

    externos = [e for e in entregas if e.tem_canal_externo]
    primeira = primeiras[0] if primeiras else None
    externo = externos[0] if externos else None

    report.tokens = tokens
    if carimbos:
        report.started_at = min(carimbos).isoformat()
        report.final_at = max(carimbos).isoformat()
        report.time_to_final_s = (max(carimbos) - min(carimbos)).total_seconds()
    if primeira:
        report.first_time_at = primeira.ts.isoformat()
        if carimbos:
            # Envelope pelo MENOR carimbo: usar "o da primeira linha" produzia
            # duração negativa em transcript fora de ordem.
            report.time_to_first_time_s = (primeira.ts - min(carimbos)).total_seconds()
    if externo:
        report.first_external_at = externo.ts.isoformat()
        report.first_external_tool = externo.canal

    corte = primeira.idx if primeira else (externo.idx if externo else idx)
    opacos = sorted(
        {n for e in entregas if e.idx <= corte for n in e.opacos}
    )
    report.unclassified_mcp_before_first_time = opacos

    report.verdict, report.reason = _verdict(
        variant,
        primeira.idx if primeira else None,
        externo.idx if externo else None,
        opacos,
    )
    return report


def _verdict(
    variant: str,
    first_time_idx: int | None,
    first_external_idx: int | None,
    opacos: list[str] | None = None,
) -> tuple[str, str]:
    """A regra do ASSERT, em unidade de ENTREGA.

    A fronteira é o record do assistente, não a posição do bloco: `[texto,
    tool_use]` na mesma mensagem é UMA resposta, e aprová-la certificaria
    exatamente a interpretação de "dois tempos na mesma resposta" que a #284
    revogou.
    """
    if variant == VARIANT_SINGLE:
        return (
            VERDICT_NOT_APPLICABLE,
            "host de resposta única: o contrato de duas entregas não se aplica",
        )

    if first_time_idx is None:
        if first_external_idx is None:
            return (
                VERDICT_MISSING,
                "nenhum canal externo aberto, e nenhuma entrega encerrada pela "
                "sentinela — em host de dois tempos o primeiro tempo é "
                "obrigatório mesmo sem email/agenda a consultar",
            )
        return (
            VERDICT_NOT_EMITTED,
            "canal externo aberto e nenhuma entrega anterior foi encerrada "
            "pela sentinela do primeiro tempo",
        )

    if first_external_idx is not None and first_external_idx <= first_time_idx:
        return (
            VERDICT_NOT_EMITTED,
            "canal externo aberto na mesma entrega do primeiro tempo, ou antes "
            "dela — entregar junto não é entregar antes",
        )

    if opacos:
        return (
            VERDICT_UNSUPPORTED,
            "não dá para certificar: houve chamada MCP de servidor opaco "
            f"antes da entrega ({', '.join(opacos[:3])}) — pode ter sido "
            "Gmail/Calendar e o nome não permite saber",
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
    parser.add_argument(
        "--since",
        help="ISO-8601 com fuso: ignora records anteriores. Necessário quando "
        "o transcript cobre mais de um briefing.",
    )
    args = parser.parse_args(argv)

    since = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
        except ValueError:
            print(f"--since não é ISO-8601: {args.since!r}", file=sys.stderr)
            return 2
        if since.tzinfo is None:
            print("--since precisa de fuso", file=sys.stderr)
            return 2

    if not args.transcript.is_file():
        print(f"transcript não encontrado: {args.transcript}", file=sys.stderr)
        return 2

    try:
        report = analyse(args.transcript, variant=args.variant, since=since)
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
    return EXIT_CODES.get(report.verdict, 3)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
