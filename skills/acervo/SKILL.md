---
name: acervo
description: >
  Navegador do "limbo" do Prumo: ideias soltas, itens da pauta que estão
  hibernando e referências guardadas que entraram e pararam. Gera um documento
  HTML offline onde o usuário NAVEGA de forma ordenada (busca, filtro por grupo,
  ordenação por idade) e revisita conteúdo parado — marcando cada item com um de
  três verbos (incluir na pauta, atacar agora, excluir), comenta, clica "copiar
  respostas" e cola de volta; o Prumo então executa o que foi garimpado. Use
  quando o usuário disser "quero revisitar minhas ideias", "abre o acervo", "ver
  o que ficou parado", "garimpar o limbo", "/acervo", ou quando quiser passar os
  olhos no acervo de coisas soltas. NÃO é para despachar a pauta do dia (isso é
  `decidir`) nem para o briefing.
---

# Acervo

Navegação e garimpo do limbo num documento HTML interativo. Forkado da mecânica
verificada do `decidir`, mas com outro propósito: o `decidir` despacha a pauta
do dia; o `acervo` deixa você **revisitar o que ficou parado** — ideias soltas,
itens hibernando, referências guardadas — de forma ordenada, e resgatar, atacar
ou descartar.

## Por que o formato existe

O limbo está espalhado (`IDEIAS.md`, a seção `Hibernando` da `PAUTA.md`,
`Referencias/`) e raramente revisitado. Despejar tudo no chat é ilegível. O
documento dá busca, filtro, ordenação por "o que está parado há mais tempo", e
um veredito clicável por item — devolvendo **um relatório único e não-ambíguo**
com um bloco JSON que o Prumo lê sem adivinhar.

## O ciclo

```
1. ENUMERAR  → `prumo acervo --workspace <ws> --format json` lê o limbo durável
2. GERAR     → preencher o template com os itens; escrever o HTML em .prumo/state/acervo/
3. ENTREGAR  → linkar o arquivo; o usuário abre no PRÓPRIO browser, offline
4. GARIMPAR  → usuário navega, marca verbo por item, comenta, "Copiar respostas"
5. RECEBER   → usuário cola o relatório; o Prumo lê o bloco JSON
6. EXECUTAR  → aplicar em camadas (ver "Receber e executar")
```

O agente **não renderiza** nada. Escreve um arquivo e lê o texto colado de
volta. Funciona em qualquer host (Cowork/Claude Code, Codex, Antigravity,
headless): o arquivo é local, o browser é o do usuário.

## Fontes — o "limbo durável"

O enumerador (`prumo acervo --format json`) lê três fontes **duráveis**:

- `IDEIAS.md` — ideias soltas sem próxima ação (fragmentos)
- seção `## Hibernando` da `PAUTA.md` (fragmentos)
- `Referencias/` — guardados com motivo+tag (arquivos inteiros), **exceto os
  operacionais** (`INDICE.md`, `EMAIL-CURADORIA.md`, `WORKFLOWS.md`)

**Fora do escopo:** `Arquivo/` (histórico já concluído) e o `_processed.json`
do inbox (cache volátil que a `faxina` apaga). Não use esses como fonte.

Se o runtime não estiver disponível, o agente lê os Markdown direto (mesmas três
fontes, mesmo escopo negativo) — a skill é portável.

## Como gerar

Use `assets/template.html`. A mecânica (estado em localStorage, busca/filtro/
ordenação, relatório markdown + JSON, clipboard) já é verificada — **preencha,
não reescreva**.

1. **Rode o enumerador** e use o JSON como fonte dos itens. Cada item já vem com
   a **proveniência** (`source_path`, `anchor`, `line_start`, `line_end`,
   `content_hash`) — não invente nem descarte esses campos; eles sustentam a
   remoção segura.

2. **Injete os itens** no lugar de `/*__ITEMS__*/`, no formato do contrato
   (`item_id`, `source_kind`, `source_path`, `anchor`, `line_start`,
   `line_end`, `content_hash`, `title`, `snippet`, `age_days`, `tags`). O
   template agrupa por `source_kind`, dá busca/filtro/ordenação e os 3 verbos.

3. **Preencha CONFIG e os placeholders:**
   - `storageKey` **única por rodada**: `prumo-acervo-<data>-<hora>-<hash-curto>`.
     Duas rodadas no mesmo dia precisam de chaves diferentes, senão o estado
     contamina.
   - `__REPORT_TITLE__`, `__HEADLINE__`, `__META__`, `__HOWTO__` etc. em PT.

4. **Salve e mantenha offline:**
   - Caminho: `.prumo/state/acervo/acervo-<data>-<hora>-<hash>.html`. **Nunca**
     em pasta de build.
   - **Copie `assets/Boliand.otf` para a mesma pasta do HTML** (o `@font-face`
     referencia `Boliand.otf` relativo). Sem a cópia, o título cai no fallback
     de sistema — funciona, só perde o display da marca.
   - **Sem rede na mecânica.** Fontes/JS/CSS não dependem de rede. O conteúdo do
     usuário (títulos/snippets) é texto local, sempre escapado.

5. **Verifique antes de entregar:** nº de `<article class="card">` == nº de itens
   visíveis; valide que o bloco JSON `prumo_acervo_report.v1` carrega a
   proveniência. Avise que o estado salva por origem (começar e terminar no
   mesmo `file://`).

## Como apresentar

Entregue com: caminho do arquivo, o que tem dentro (nº de itens por grupo), como
o feedback volta (garimpar → **"Copiar respostas"** → colar na conversa), e a
promessa: **o que vier marcado no relatório, o Prumo executa** — com a exceção
de remoção (sempre confirma e arquiva, nunca apaga no escuro).

## Receber e executar

Quando o usuário colar o relatório:

1. **Leia o bloco JSON** (`prumo_acervo_report.v1`), não a prosa. Cada item traz
   `item_id`, `verb` (`include_pauta` | `attack_now` | `delete`), a
   **proveniência** (`source_path`, `anchor`, `line_start`, `line_end`,
   `content_hash`) e `comment`.

2. **Execute por verbo:**
   - **`include_pauta`** — adicionar o item à `PAUTA.md` como entrada acionável
     (seção `Horizonte` por padrão, salvo o comentário pedir outra). Direto, sem
     reconfirmar. Use `prumo acervo --workspace <ws> apply` ou edite a
     `PAUTA.md` à mão.
   - **`attack_now`** — trabalhar o item agora, na sessão (desenvolver a ideia,
     começar a tarefa). Julgamento do agente; não é mecânico.
   - **`delete`** — **arquivar, não apagar.** Remoção segura, nesta ordem:
     1. Reabrir o `source_path`, localizar o item pela `anchor`/linhas, e
        **comparar o `content_hash` atual com o do relatório**.
     2. Se o hash **não bate** (o arquivo mudou desde a geração) **ou** o trecho
        aparece em **mais de um lugar** → **bloquear e pedir revisão**. Não
        adivinhar qual remover.
     3. Confirmar o plano com o usuário e **registrar no `REGISTRO.md`** antes de
        remover o original (ASSERT do core).
     4. **Mover** o fragmento/arquivo para `Prumo/Arquivo/Acervo/` (quarentena).
        Deleção **permanente** só se o usuário escrever explicitamente "apagar
        permanentemente".
   - O runtime expõe isso testado: `prumo acervo --workspace <ws> apply
     --report <arquivo.json>` (e `--permanent` só sob pedido explícito).

3. **Comentário é instrução.** "Incluir na pauta" + comentário = incluir daquele
   jeito (prazo, seção, contexto).

4. **Feche informando o estado:** o que foi incluído, o que foi atacado, o que
   foi arquivado (e onde), o que ficou bloqueado por hash divergente.

## Referências

- `assets/template.html` — o template (mecânica verificada; preencha, não reescreva).
- `references/acoes-acervo.md` — os 3 verbos, suas camadas de execução e o
  contrato de proveniência/remoção segura.
