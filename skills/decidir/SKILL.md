---
name: decidir
description: >
  Superfície de decisão interativa do Prumo: quando há muitos itens para
  despachar de uma vez (briefing com 6+ itens acionáveis, triagem de inbox,
  uma pilha de pendências), gera um documento HTML offline onde o usuário
  decide item a item — com ações contextuais por item (responder, arquivar,
  adiar, delegar, confirmar, descartar...) — comenta, clica "copiar respostas"
  e cola de volta; o Prumo então executa o que foi despachado. Use quando o
  briefing produzir 6+ itens acionáveis, quando o usuário pedir "quero decidir
  no visual", "gera o decidir", "me dá o HTML pra despachar", "abre no decidir",
  ou quando uma triagem/revisão gerar muitas decisões individuais que ficariam
  confusas se despachadas em prosa no chat. NÃO dispara para uma decisão isolada
  no meio de conversa nem para feedback sobre o produto Prumo.
---

# Decidir

Despacho e decisão em lote num documento HTML interativo. Forkado da mecânica do `crivo` e adaptado ao Prumo: ao invés de aprovar/ajustar/rejeitar uma crítica, o usuário **despacha** cada item com a ação que faz sentido para ele (responder, arquivar, adiar, delegar, confirmar, descartar...). O nome diz o trabalho: tirar o usuário da paralisia de uma pilha de itens, um veredito clicável por vez.

## Por que o formato existe

Despachar 8 itens em prosa no chat mistura decisões e força o Prumo a adivinhar o que foi resolvido. O documento dá ao usuário um botão por item, um comentário por item, e devolve **um relatório único e não-ambíguo** — com um bloco JSON que o Prumo lê sem interpretar recibo amassado.

## O ciclo

```
1. GERAR     → escrever o HTML preenchido em .prumo/state/decidir/
2. ENTREGAR  → linkar o arquivo; o usuário abre no PRÓPRIO browser, offline
3. DECIDIR   → usuário despacha item a item, comenta, clica "Copiar respostas"
4. RECEBER   → usuário cola o relatório; o Prumo lê o bloco JSON
5. EXECUTAR  → aplicar o despachado em camadas (ver "Receber e executar")
```

O agente **não renderiza** nada. Ele escreve um arquivo e lê o texto colado de volta. Por isso funciona em qualquer host (Claude Code/Cowork, Codex, Antigravity, headless): o arquivo é local, o browser é o do usuário.

## Quando gerar

- **No briefing:** quando houver **6+ itens acionáveis** (conta só item que pede decisão — não evento informativo). Abaixo disso, despachar em chat sai mais barato que abrir HTML. Veja a integração em `skills/briefing` / `briefing-procedure.md`.
- **Override do usuário, sempre respeitado:** "quero visual" / "gera o decidir" / "me dá o HTML" → gerar mesmo com poucos itens. "resolve no chat" / "sem HTML" / "modo chat" → não gerar. Sinais conflitantes na mesma mensagem → perguntar "visual ou chat?" em uma linha.
- **Fora do briefing:** triagem de inbox grande, uma pilha de pendências, qualquer momento com muitas decisões individuais.

Se a geração falhar (não conseguiu escrever o arquivo), **cair no despacho em chat** — nunca travar o fluxo.

## Como gerar

Use `assets/template.html`. A mecânica (estado em localStorage, ações por-card, relatório markdown + JSON, clipboard) já é verificada — **preencha, não reescreva**.

1. **Reuse os números do panorama.** No briefing, o item numerado `7` do panorama vira o card de `id: '7'`. O usuário responde "o 7" no mesmo número que viu no chat. Nunca renumerar.

2. **Escolha tipo e ações por item:**
   - **`despacho`** — a maioria dos itens. Traz `actions: [{key, label, tone, effect, requires?}]`. As ações vêm da **allowlist por tipo** em `references/acoes-allowlist.md` — **selecione de lá, nunca invente verbos**. Só ofereça ações que cabem naquele item (ex.: `Delegar` só com destinatário; `Confirmar/Recusar` só em convite com RSVP, não em evento do dia comum).
   - **`escolha`** — decisões entre alternativas (foco do dia, qual caminho). Opções A/B/C com **texto final** e uma `rec: true`.

3. **Preencha CONFIG e os placeholders:**
   - `storageKey` **única por rodada**: `prumo-decidir-<data>-<hora>-<hash-curto>` (ex.: `prumo-decidir-2026-06-23-0830-a1b2`). Dois briefings no mesmo dia precisam de chaves diferentes, senão o estado contamina.
   - `__REPORT_TITLE__`, `__HEADLINE__`, `__META__`, `__HOWTO__` etc. em PT.

4. **Salve e mantenha offline:**
   - Caminho: `.prumo/state/decidir/briefing-<data>-<hora>-<hash>.html`. **Nunca** em pasta de build (`public/`, `dist/`, `static/`).
   - **Copie `assets/Boliand.otf` para a mesma pasta do HTML** (o `@font-face` referencia `Boliand.otf` relativo). Sem a cópia, o título cai no fallback de sistema — funciona, só perde o display da marca.
   - **Sem rede.** Nenhuma URL `http(s)://` no arquivo. Não adicionar Google Fonts, CDN ou analytics. O usuário abre offline, possivelmente sem internet.

5. **Verifique antes de entregar** (a entrega é um artefato — entregue testado):
   - **Contagem:** nº de `<article class="card">` renderizados == nº de entradas em `POINTS`. Se renderizou menos, quase sempre há uma tag HTML literal não-escapada no conteúdo (ex.: `<title>` cru) engolindo os cards seguintes — escape como `&lt;title&gt;`.
   - Se houver browser/preview, clique uma ação, gere o relatório, confira que o bloco JSON `prumo_decidir_report.v1` tem os itens certos. Senão, no mínimo valide a contagem e `node --check` num extrato do script.
   - Avise o usuário que o estado salva por origem: começar a responder via `file://` e terminar lá (`localhost` cria storage separado).

## Como apresentar

Entregue com: caminho do arquivo, o que tem dentro (nº de itens, seções), como o feedback volta (decidir → **"Copiar respostas"** → colar na conversa), e a promessa que sustenta o ciclo: **o que vier despachado no relatório, o Prumo executa** — com as exceções de confirmação abaixo.

## Receber e executar

Quando o usuário colar o relatório:

1. **Leia o bloco JSON** (`prumo_decidir_report.v1`), não a prosa. Cada item traz `item_id`, `action_key`/`choice_key`, `label`, `effect`, `requires`, `comment`.
2. **`requires` não satisfeito:** se a ação exige um detalhe (`requires`) e o `comment` não traz (ex.: `Delegar` sem destinatário, `Aguardar até` sem data), **pedir o detalhe antes de executar** — não chutar.
3. **Execute em camadas — a promessa "executo sem perguntar de novo" tem limite:**
   - **Direto (sem nova confirmação):** rascunhar resposta/cobrança (sem enviar), registrar, marcar visto, virar pauta/tarefa, adiar, arquivar **com destino explícito**.
   - **Confirmar antes de executar:** enviar email ou cobrança de fato, recusar/remarcar evento com terceiros, e **qualquer remoção de item de inbox** (`arquivar`/`descartar`) — o core exige confirmar o plano e registrar no `REGISTRO.md` antes de remover o original (ASSERT). Botão de despacho não é procuração para mandar mensagem ou apagar arquivo sem o usuário ver.
4. **Comentário é instrução.** "Responder" + comentário = responder daquele jeito. Pergunta no comentário exige resposta concreta.
5. **Feche informando o estado:** o que foi aplicado, o que foi só rascunhado/aguardando confirmação, o que ficou sem resposta.

## Referências

- `assets/template.html` — o template (mecânica verificada; preencha, não reescreva).
- `references/acoes-allowlist.md` — allowlist de ações por tipo de item, com `effect`, `requires` e risco. **Selecione daqui; não invente verbos.**
- `references/exemplos-de-cards.md` — cards reais de referência (bons e ruins) para `despacho` e `escolha`.
