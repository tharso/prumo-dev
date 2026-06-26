---
name: fim
description: >
  Encerramento formal de sessão do Prumo. Quando o usuário diz "/fim", "terminar
  por hoje", "encerrar a sessão", "fechar o dia", "acabei", a skill documenta os
  deltas duráveis da sessão nos canais existentes (sem perder ideia ou status
  entre sessões), roda a faxina automática, mostra um resumo, e — se detectar
  acúmulo — PROPÕE (não executa) `/higiene` ou `/sanitize`. É o bookend
  simétrico do briefing: o briefing abre, o fim fecha. NÃO é briefing (não lê
  email/calendário, não monta a pauta do dia) e NÃO cria artefato narrativo de
  sessão.
---

# Fim

Encerramento de sessão. Porta única que resolve dois problemas: (a) ideias e
status discutidos na sessão **evaporam** entre sessões; (b) os comandos de
limpeza (`faxina`, `higiene`, `sanitize`) ficam **esquecidos** e o workspace
acumula lixo. O `/fim` é o bookend do `/briefing` — um abre o dia, o outro fecha.

## Contrato conservador (anti-evaporação honesta)

Documentar a sessão **não** é reconstruir o que foi dito de memória. Contexto é
volátil — compactação destrói memória textual (ver CLAUDE.md). Então o `/fim`
segue um procedimento **verificável**, não fé na própria honestidade:

1. **Listar candidatos** a delta durável — decisões tomadas, itens criados ou
   mudados — **com a origem visível** na sessão (não do nada).
2. **Confirmar** um resumo curto com o usuário antes de gravar.
3. **Gravar só o confirmado**, nos **canais que já existem**:
   - ideia sem próxima ação → `IDEIAS.md`
   - tarefa nova / mudança de status → `PAUTA.md`
   - fato / decisão / trabalho concluído → `REGISTRO.md`
4. **Sob compactação:** se a sessão foi compactada, o default é **não registrar
   fato anterior ao trecho visível** — declarar a lacuna ao usuário ("não
   consigo garantir o começo da sessão"). A ressalva é cinto de segurança, não
   licença pra dirigir no escuro.

**Proibido (mantém a #68):** reconstruir sessão no escuro; criar "resumo
narrativo de sessão"; gerar qualquer artefato narrativo (`HANDOVER`,
`PENDING_VALIDATION`, doc de sessão) em `skills/`, `runtime/` ou
`.prumo/state/`. O `/fim` grava **fatos em canais existentes**, nada de narrativa.

## O fluxo

```
1. DOCUMENTAR → deltas visíveis e confirmados → IDEIAS / PAUTA / REGISTRO
2. FAXINA     → roda a rotina automática (já é no-confirm)
3. RESUMO     → o que registrou + o que a faxina arrumou
4. DETECTAR   → `prumo fim --format json` aponta acúmulo; PROPOR higiene/sanitize
```

### Passo 2 — Faxina (automático)

Rodar a `faxina` (rotaciona REGISTRO, migra pauta concluída, atualiza índices,
limpa processados antigos). É a limpeza que **não exige julgamento** — corre
sozinha, como já corre no início do briefing.

### Passo 4 — Detecção de acúmulo (propõe, não executa)

Rodar `prumo fim --workspace <ws> --format json` (read-only). Ele computa sinais
determinísticos reusando os thresholds da faxina/sanitize:

- `pauta_stalled` (itens parados > 14d) e `inbox_pending` → sugerem **`/higiene`**
- `backups_old` (> 90d) e `ephemeral_html_old` (HTMLs do decidir/acervo > 14d) →
  sugerem **`/sanitize`**

Quando `suggest.higiene` ou `suggest.sanitize` vier `true`, **oferecer** o
comando ao usuário — uma linha, escolha curta. **Nunca executar** `higiene`/
`sanitize` por conta própria: elas pedem julgamento/aprovação. O `/fim` só
aponta e delega; não duplica a detecção da higiene nem roda a sanitize.

Se o runtime não estiver disponível, o agente faz a checagem lendo os arquivos
direto (mesmos thresholds) — a skill é portável.

## Cerca contra overlap com o briefing

O `/fim` é encerramento, não mini-briefing. Ele **NÃO**:

- lê email ou calendário (Gmail/Calendar MCP);
- marca `last-briefing.json` (isso é do briefing, no fim da curadoria rica);
- refaz a proposta/panorama do dia;
- duplica a detecção da higiene (só aponta e delega).

## Como apresentar

Encerrar com: o que foi **registrado** (e onde), o que a **faxina** arrumou, e —
se houver acúmulo — a **sugestão** de higiene/sanitize como escolha curta. Se a
sessão foi compactada, dizer o que **não** dá pra garantir. Fechar deixando a
próxima sessão limpa: o `/briefing` seguinte já lê `IDEIAS`/`PAUTA`/`REGISTRO`,
então o agente começa up-to-date naturalmente — sem artefato extra.

## Referências

- `prumo fim --format json` — detector de acúmulo (read-only).
- Thresholds reusados: `skills/faxina/references/thresholds.md`.
- Limpezas que o `/fim` apenas propõe: `skills/higiene/SKILL.md`,
  `skills/sanitize/SKILL.md`.
