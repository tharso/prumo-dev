# Briefing Procedure (espinha da rota fásica)

> **module_version: 5.1.0**
>
> Fonte canônica do procedimento de briefing do Prumo — a ESPINHA (#180):
> identidade, ordem dos passos e gates. O detalhe de cada fase mora nos
> módulos de fase (`briefing-estado.md`, `briefing-canais.md`,
> `briefing-montagem.md`, `version-preflight.md`) e carrega **na fase que o
> usa** — o mapa único de carregamento é o `## Mapa de carregamento por
> fase` do `skills/briefing/SKILL.md` (#195 emendada pela #180: a lista
> canônica virou o mapa; este módulo NÃO mantém segunda enumeração).
> Se este módulo conflitar com um resumo em `SKILL.md`, este módulo vence.
> Se este módulo conflitar com um `ASSERT:` do `.prumo/system/PRUMO-CORE.md`, o `ASSERT:` vence.

## Numeração (resumo operacional — dono: `interaction-format.md`)

Todo item acionável recebe número sequencial único, do primeiro ao último, sem reiniciar entre seções **nem entre os dois tempos (#196)** — pendências e inbox no primeiro tempo (1..k), emails e agenda no segundo (k+1..N), continuando de onde parou; o despacho em lote ("3, 7, 12") mistura os dois tempos. Sem sub-numeração, sem reinício; elemento estrutural (abertura, avisos, proposta) não numera. A regra completa, com exemplos, mora em `interaction-format.md` (carrega na montagem, F3).

## Passo 0: o runtime é prévia, não é o briefing

O cartão do runtime (`prumo start` / `prumo briefing`) é a **prévia** — retrato rápido e local. O **briefing** é a curadoria rica desta rota: email e agenda + panorama numerado único → `decidir`.

1. **Nunca** entregar a saída do runtime como briefing final nem encerrar nela — o usuário pediu o briefing, não a prévia. O JSON do runtime é **painel local** (semente); a resposta é sempre o panorama rico.
2. **Sem MCP de email/agenda:** panorama com o que há localmente + **declarar em uma linha** a indisponibilidade, orientando reestabelecer o acesso ou checar a agenda à mão. Não mascarar: silêncio passaria por "agenda vazia" quando é "agenda não lida". Nunca voltar ao cartão da prévia como "solução".
3. A marcação do dia (`--mark-done`), a tabela de variantes e a proibição de marcar sem runtime (#214) moram no fechamento da montagem (`briefing-montagem.md`).

## Passo 1: configuração e data local

1. Extrair timezone do `Prumo/Agente/PERFIL.md` (default: `America/Sao_Paulo`).
2. Resolver data local por fonte verificável: ferramenta de tempo com timezone; relógio do sistema com TZ explícito; APIs de calendário no mesmo fuso.
3. Se não houver fonte confiável, não anunciar dia/data textual no cabeçalho.
4. Se `Prumo/Agente/PERFIL.md` ou `.prumo/system/PRUMO-CORE.md` não existirem, interromper e orientar o usuário a rodar o setup.

## Passo 2: preflight de versão

Executar o preflight de `version-preflight.md` (F1 — já carregado): transporte da comparação (runtime produtor 1x/24h, ou `VERSION` público sem runtime), gatilho graduado por severidade e o protocolo do remoto suspeito (#215). O preflight **roda sempre**; `version-update.md` (o manual completo) só carrega quando a oferta aciona (`warning`/`alert`) ou o usuário responde a ela. A oferta, quando existe, **abre o primeiro tempo — e o briefing segue na MESMA resposta**.

## Passo 3: estado operacional

Montar o retrato local por `briefing-estado.md` (F1 — já carregado). Os gates, em uma linha cada:

1. **Semente viva** (runtime alcançável — Passo 0): gate por CAPACIDADE — `schema_version` v1, `outras_secoes` lista **e** `indice_referencias.schema`; capenga → fallback direto.
2. **Arquivo-semente** `.prumo/state/local-panorama.json` (#216): gate TRIPLO — capacidade + `generated_for` == hoje + frescor POR FONTE (`source_mtimes` + `inbox4mobile_manifest`); o agente **nunca** escreve esse arquivo.
3. **Leitura direta** (`PAUTA.md` + `INBOX.md`) quando não há semente válida — nunca inventar dado de JSON parcial.

A checagem de faxina (cinco famílias, linha SEMPRE declarada — #217) e o filtro de cobrança estão no mesmo módulo.

## Fase F2: canais de entrada

**Carregar `briefing-canais.md` antes da triagem local do Inbox4Mobile OU de abrir qualquer canal externo (Gmail/Calendar MCP)** — o que vier primeiro; sem MCP nenhum, o estágio local do inbox ainda é F2 e exige o módulo. Defesas de terceiros (#156) e pós-filtro exato (#210) moram no MESMO arquivo das queries. O estágio LOCAL do Inbox4Mobile (inventário + triagem leve, sem abrir bruto) roda antes do primeiro tempo; com itens novos, `inbox-processing.md` carrega junto; a detecção de divergência agenda×email (#211) também é daqui.

## Fases F3 e F4: montagem e fechamento

**Ao montar o panorama (F3), carregar `briefing-montagem.md` e `interaction-format.md`**: dois tempos (#196), escape, variantes, linha de faxina (#217), apresentação da divergência (#211), despacho visual automático 6+ (#218), proposta do dia. **F4 (fechamento)** não carrega material novo — executa a seção `## Escrita e fechamento` da montagem (escrita nos canais, `_processed.json`, marcação do dia #214). Pauta vazia → brain dump obrigatório (lá).
