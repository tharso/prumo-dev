---
name: decidir
user-invocable: false
description: >
  Superfície de decisão interativa do Prumo — normalmente é o briefing que a
  abre sozinho; você também pode pedir. Quando há muitos itens para
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
   - **`despacho`** — a maioria dos itens. Traz `actions: [{key, label, tone, effect, requires?}]`. As ações vêm da **allowlist por tipo** em `references/acoes-allowlist.md` — **selecione de lá, nunca invente verbos**. `effect` é o token canônico (snake_case) da allowlist, não prosa. Só ofereça ações que cabem naquele item: `Delegar` traz `requires: 'destinatário'` (o usuário informa no comentário) — não ofereça se não houver a quem delegar; `Confirmar/Recusar` só em convite com RSVP, não em evento do dia comum.
     - **Itens de inbox: classifique o CONTEÚDO** (vídeo / artigo-link / imagem / nota) e use o **menu por conteúdo** da allowlist — não o genérico. Um vídeo recebe `Extrair/transcrever` e `Resumir`, não "virar referência".
     - **Itens de inbox: mostre o item ou leve a ele — mostrar ≠ analisar.** Nota **até ~400 caracteres** vai **integral** no campo **`conteudo_b64`** do card — o texto codificado em **base64 (UTF-8)** por comando **em linha única** (`printf '%s' "$texto" | base64 | tr -d '\r\n'` — o `tr` remove o newline final e as quebras de 76 colunas do GNU base64 — ou `python3 -c` com `base64.b64encode`), nunca "à mão"; o template decodifica e escapa no render, e o alfabeto do base64 garante que o texto do usuário não quebra nem injeta o documento. **Nunca** colar texto de terceiro em `contexto`/`evidencia` (markup do gerador). Nota mais longa: os primeiros ~400 caracteres (corte em fronteira de palavra) em `conteudo_b64` + link pro arquivo. Conteúdo não-elementar (imagem/vídeo/post) traz metadados + o **link do item** no campo estruturado `link: {label, href}` (o template o renderiza ativo e sanitizado; arquivo local do workspace entra como path **relativo** à pasta do HTML — absoluto o `safeUrl` rejeita). Card que só descreve o item, **sem conteúdo nem link**, é inválido — o usuário não despacha o que não vê. E **não** abrir/transcrever/OCR na geração: análise pesada é ação pós-despacho da allowlist, paga só se despachada. Thumbnail/embed fica para fatia futura.
   - **`escolha`** — decisões entre alternativas (foco do dia, qual caminho). Opções A/B/C com **texto final** e uma `rec: true`.
   - **Default do detalhe (#246):** ao montar a ação, preencha `default` quando houver valor óbvio — `discard` sempre leva `"não interessa mais"`; `keep_with_reason` só leva default quando o card **já exibe motivo e tag concretos** inferidos do item (sem os dois, deixe sem default: `requires_missing` cobra, e a ficha canônica manda perguntar). O relatório devolve `default_used` + `resolved_detail`; comentário digitado vence o default.

3. **Preencha CONFIG e os placeholders:**
   - `storageKey` **única por rodada**: `prumo-decidir-<data>-<hora>-<hash-curto>` (ex.: `prumo-decidir-2026-06-23-0830-a1b2`). Dois briefings no mesmo dia precisam de chaves diferentes, senão o estado contamina.
   - `__REPORT_TITLE__`, `__HEADLINE__`, `__META__`, `__HOWTO__` etc. em PT.

4. **Salve e mantenha offline:**
   - Caminho: `.prumo/state/decidir/briefing-<data>-<hora>-<hash>.html`. **Nunca** em pasta de build (`public/`, `dist/`, `static/`).
   - **Copie `assets/Boliand.otf` para a mesma pasta do HTML** (o `@font-face` referencia `Boliand.otf` relativo). Sem a cópia, o título cai no fallback de sistema — funciona, só perde o display da marca.
   - **Sem rede na mecânica.** A mecânica do documento (fontes, JS, CSS) **não pode depender de rede** — nada de Google Fonts, CDN ou analytics; a fonte é local (`Boliand.otf` copiada). **Mas os links de conteúdo do usuário vêm ATIVOS** (`<a href="…" target="_blank" rel="noopener">`): vídeo, artigo, qualquer URL que o item carrega. A regra offline protege a mecânica, não cega o conteúdo — card com link inerte é triagem no escuro.

5. **Verifique antes de entregar** (a entrega é um artefato — entregue testado):
   - **Rode o validador:** `node skills/decidir/validate-cards.mjs <arquivo.html>` (no workspace: `.prumo/skills/decidir/validate-cards.mjs`). Ele confere o que engole cards antes de eles sumirem — tag não permitida ou `<` solto nos campos de markup, `sec` que não existe em `SECTIONS` (esse card some **em silêncio**, sem erro e sem console), id ou chave de ação repetida, `conteudo_b64` com quebra de linha. Roda em milissegundos, sem rede. **Não conte `<article class="card">` com `grep`:** essa string existe uma única vez no arquivo, dentro do template — a contagem daria 1 com 29 cards ou com zero.
   - **Card sem escuro (todo card baseado em fonte, não só inbox):** item de inbox tem `conteudo_b64` inline **ou** `link` ativo de visualização; email tem **remetente + trecho citável** (ou link pra thread); evento tem o dado que sustenta a decisão (horário, quem convida). Card que só descreve a fonte, sem conteúdo nem link, não sai — meta-descrição de gravata ainda é triagem no escuro.
   - **Ações que cabem:** `Delegar` só com **delegado plausível** no contexto do item; `Confirmar/Recusar` só com RSVP. Fileira idêntica à tabela da allowlist é sinal de que faltou filtrar.
   - **NUNCA instalar browser, runtime ou dependência para validar.** Nada de `npm i`, download de Chromium, Playwright ou equivalente: um briefing real gastou **186 segundos** (28% do relógio) fazendo isso — para conferir o que o validador acima confere em milissegundos. O agente **não renderiza** (ver o topo desta skill); "se houver browser" significa aproveitar um que já exista, nunca fabricá-lo.
   - Escada de verificação, do mais barato ao mais caro: **(1)** validador — sempre, é o que fecha a classe de defeito; **(2)** sem `node` no host, entregar assim mesmo e **declarar em uma linha** que a validação não rodou (degradação honesta vale mais que instalação silenciosa); **(3)** só se já houver browser/preview aberto, clicar uma ação, gerar o relatório e conferir que o bloco JSON `prumo_decidir_report.v1` tem os itens certos.
   - Avise o usuário que o estado salva por origem: começar a responder via `file://` e terminar lá (`localhost` cria storage separado).

## Como apresentar

Entregue com: caminho do arquivo, o que tem dentro (nº de itens, seções), como o feedback volta (decidir → **"Copiar respostas"** → colar na conversa), e a promessa que sustenta o ciclo: **o que vier despachado no relatório, o Prumo executa** — com as exceções de confirmação abaixo.

## Receber e executar

Quando o usuário colar o relatório:

1. **Leia o bloco JSON** (`prumo_decidir_report.v1`), não a prosa. Cada item de despacho traz `item_id`, `action_key`, `label`, `effect` (token canônico — aja por ele), `requires`, `requires_missing`, **`source_url`/`source_label`** (a URL do conteúdo — vídeo/artigo — pra `extract_transcript`/`summarize`/`open_link` saberem QUAL item, mesmo em sessão nova) e `comment`; os de `escolha` trazem `choice_key`, `choice_label`, `effect`, `source_url`/`source_label`.
2. **`default_used: true` (#246):** a ação tinha default no card e o usuário não digitou nada — o detalhe está em **`resolved_detail`** (valor concreto: agir por ele, não adivinhar). No registro, distinguir do motivo autoral: *"descartado (padrão: não interessa mais)"*. `comment` preenchido significa texto do usuário e **vence** o default.
3. **`requires_missing: true`:** a ação exige um detalhe (`requires`) que o usuário não preencheu no comentário (ex.: `Delegar` sem destinatário, `Aguardar até` sem data). **Pedir o detalhe antes de executar** — não chutar.
4. **Execute em camadas — a promessa "executo sem perguntar de novo" tem limite:**
   - **Direto (sem nova confirmação):** rascunhar resposta/cobrança (sem enviar), registrar, marcar visto, virar pauta/tarefa, adiar, arquivar **com destino explícito**.
   - **Confirmar antes de executar:** enviar email ou cobrança de fato, recusar/remarcar evento com terceiros, e **qualquer remoção de item de inbox** (`arquivar`/`descartar`) — o core exige confirmar o plano e registrar no `REGISTRO.md` antes de remover o original (ASSERT), e remover é **mover** (destino durável ou quarentena `_to_delete/` — `inbox-processing.md`), nunca deletar. Botão de despacho não é procuração para mandar mensagem ou dar baixa em arquivo sem o usuário ver.
5. **Efeitos de conteúdo (itens de inbox) — quem analisa é o próprio Claude, sem API externa:**
   - `extract_transcript` (vídeo): **soft-hook**, nesta ordem — (a) `youtube-transcript-api` se disponível (legendas grátis, **sem API key**); (b) fetch da página pra título/descrição/capítulos; (c) se nada, abrir + virar tarefa com prazo. Depois o Claude resume. **Nunca** exigir API do Google, yt-dlp, ffmpeg ou Whisper.
   - `summarize` / `debate`: o Claude resume ou debate o conteúdo acessível (transcript/artigo). Sem acesso, dizer isso e oferecer abrir — não inventar resumo.
   - `describe_image`: o Claude descreve / extrai texto (OCR) da imagem que ele já consegue ler.
   - `keep_with_reason`: só guardar **com motivo + tag** (o `requires`). Sem isso, não é referência — é buraco negro.
   - `make_idea`: fragmento **sem próxima ação** → `IDEIAS.md`, nunca `PAUTA.md`.
   - `open_link`: apenas **apresentar o link ativo** (`source_url`) ao usuário pra ele abrir. Não marca o item como processado — é só abrir, a decisão real fica pra depois.

   **Links de conteúdo:** ao gerar os cards, use o **campo estruturado `link: {label, href}`** (o template sanitiza via `safeUrl` e escapa o label). **Não** cole `<a>` cru no `contexto`/`evidencia` — inbox é entrada do usuário; HTML cru é porta lateral.
5. **Comentário é instrução.** "Responder" + comentário = responder daquele jeito. Pergunta no comentário exige resposta concreta.
6. **Feche informando o estado:** o que foi aplicado, o que foi só rascunhado/aguardando confirmação, o que ficou sem resposta.

## Referências

- `assets/template.html` — o template (mecânica verificada; preencha, não reescreva).
- `references/acoes-allowlist.md` — allowlist de ações por tipo de item, com `effect`, `requires` e risco. **Selecione daqui; não invente verbos.**
- `references/exemplos-de-cards.md` — cards reais de referência (bons e ruins) para `despacho` e `escolha`.
