# Inbox Processing

> **module_version: 5.63.0**
>
> Fonte canônica da triagem e do commit de inbox do Prumo.

## Escopo

Vale para:

- `INBOX.md`
- `Inbox4Mobile/`
- itens de inbox detectados durante `/prumo:briefing` ou `/prumo:inbox`

## Triagem em dois estágios

### Estágio A: triagem leve

1. **Inventário real**: listar os arquivos em `Inbox4Mobile/` **com nome e `mtime`** (excluindo `_preview-index.json`, `_processed.json`, `inbox-preview.html`). Comparar com `_processed.json`. Qualquer arquivo que não esteja lá com `status: "processed"` é item novo. Não confiar no `_preview-index.json` como fonte de verdade — ele pode estar stale.
2. **Regenerar o preview exige runtime:** `prumo inbox preview` (operação explícita — o briefing nunca regenera implicitamente, #197). O gerador vive dentro do pacote `prumo_runtime`, então **em host sem runtime não há como**: não procure script, não tente caminho alternativo. Quem mantém o preview fresco é o ritual na máquina que tem o runtime.
3. **Preview velho ou ausente não suspende a triagem — e não escolhe ramo.** O ASSERT do core proíbe abrir o BRUTO no primeiro tempo; classificar por nome sempre foi permitido — e é obrigatório (`briefing-canais.md`). Cada item segue a bifurcação do passo 5 conforme a evidência que houver **dele**: o estado do preview é uma condição da FONTE, e classificar é do ITEM.
4. Linkar `inbox-preview.html` **só se ele existir e estiver utilizável** — arquivo regular, legível, não-vazio e não-symlink. O predicado é o HTML, não o índice: `status: gerado` compara mtimes e não confere a existência do arquivo, então índice fresco pode apontar um fantasma. **Sem HTML utilizável, não linkar — e só isso**: a classificação de cada item segue a bifurcação do passo 5, porque a evidência pode ter chegado por outra via (o usuário colou o conteúdo, por exemplo). O HTML decide o LINK, não decide sozinho o que se sabe do item.
5. **Para cada item novo**, classificar — e o que se pode afirmar depende do que se tem:

   O corte é **evidência material do ITEM**, não frescor da fonte. Metadata — nome, tipo, tamanho, `mtime`, fingerprint e a `first_url` do índice — **não é evidência**. URL sozinha identifica a FONTE, não ação, prazo nem consequência: um link de YouTube ou de encurtador não diz se é urgente. Ela só conta quando o que está visível (inclusive a semântica explícita da própria URL, quando houver) sustenta os três campos. Metadata ela não distingue um `IMG_1234.jpg` urgente de um print de meme. E `status: gerado` não garante conteúdo à vista: o frescor compara o `mtime` do índice com o dos arquivos e **não confere se o `inbox-preview.html` existe**. Índice fresco com preview ausente, por si só, **não prova conteúdo** — mas também não condena o item: ele só cai no ramo fraco se nenhuma outra via tiver trazido evidência material dele.

   **Com evidência** (o conteúdo do item está à vista — preview utilizável que o mostra, ou conteúdo já legitimamente em mãos — e o que se vê sustenta ação, prioridade **e** motivo):
   - ação: `Responder`, `Ver`, `Sem ação`
   - prioridade: `P1`, `P2`, `P3`
   - motivo objetivo

   **Sem evidência** (só metadata — inclusive com índice fresco, se o conteúdo não chegou a aparecer):
   - ação: só quando o **nome** a sustentar; na dúvida, `Ver`
   - prioridade: **`não determinada`**. Nunca `P1/P2/P3` de arquivo que ninguém abriu — prioridade sem evidência é chute com cara de triagem, e o custo dela é o usuário confiar num número que ninguém apurou
   - motivo: o que o nome diz, e só
   - **declarar em uma linha** que a classificação é por nome, mais a idade do item mais antigo (do `mtime` do passo 1; sem acesso a metadata, dizer que a idade está indisponível — lacuna nomeada vale mais que aniversário inventado)

   Os dois ramos entregam **triagem numerada** — o fallback degrada a certeza, nunca a entrega (`briefing-montagem.md` é o dono do formato).

### Estágio B: aprofundamento seletivo

Abrir conteúdo bruto completo apenas quando houver:

1. item `P1`;
2. ambiguidade que impeça ação segura;
3. risco legal, financeiro ou documental;
4. solicitação explícita do usuário.

## Preview multimídia

1. Se a geração falhar mas houver preview anterior **utilizável** (mesmo predicado do passo 4), linkar e avisar que pode estar defasado.
2. Se não houver preview utilizável, seguir com lista numerada no chat e registrar a falha.
3. No panorama do briefing, **não despejar conteúdo bruto** dos arquivos — link e contagem bastam para o preview em si. Isto é sobre o PREVIEW, não sobre a triagem: o formato do panorama é do `briefing-montagem.md`, e ele exige contagem **e** triagem, com itens numerados. Ler esta linha como licença para entregar só um número é o furo de 30/07.

## Commit do inbox

Depois da triagem:

1. montar um plano único de operações pendentes;
2. pedir confirmação explícita do usuário;
3. executar em lote;
4. verificar cada operação;
5. reportar fechamento do commit.

## Operações válidas

1. mover item para `PAUTA.md` ou README da área/projeto;
2. adicionar `(desde DD/MM)` ao criar item novo;
3. se for agendado futuro, registrar `| cobrar: DD/MM`;
4. renomear arquivos com nomes descritivos;
5. registrar no `REGISTRO.md`;
6. remover o original do inbox pela **máquina de remoção** abaixo — mover, nunca deletar.

## Remoção: mover, nunca deletar (#242)

Deleção real não é operação do **fluxo de inbox** — há host em que ela nem
existe (a ponte do Cowork falha com `Operation not permitted`), e o que este
fluxo promete é reversibilidade. (O `acervo` mantém o contrato próprio dele:
`--permanent` só sob pedido explícito.) O destino do original depende da ação:

- **Retenção durável** — o item vira referência com o próprio arquivo movido
  pra `Referencias/`, ou é arquivado com destino explícito: o arquivo move
  DIRETO pro destino durável. Não passa pela quarentena e nunca é duplicado.
- **Quarentena** — descarte (`discard`) ou original já materializado noutro
  canal (nota que virou linha de PAUTA/IDEIAS, conteúdo extraído/resumido):
  mover para `_to_delete/<AAAA-MM-DD>_<escopo>/` na **raiz do workspace** (o
  diretório que contém os wrappers, nos dois layouts) e informar na resposta
  os arquivos movidos — quem esvazia a quarentena é o usuário, à mão.

### Máquina de remoção (por item, nesta ordem)

1. **Confirmar** o plano único de commit (ASSERT do core).
2. **Registrar** no `REGISTRO.md`: item, ação e destino planejado — a trilha
   vem ANTES da remoção (ASSERT).
3. **Mover** o original pro destino planejado (criar a pasta datada da
   quarentena ao mover o primeiro item).
4. **Verificar**: origem ausente e destino íntegro.
5. **Marcar** o item em `Inbox4Mobile/_processed.json` (`reason` recomendado:
   `movido para quarentena`; o valor legado `fallback sem deleção física`
   continua válido em registros antigos).
6. **Se o move falhar**: registrar `REMOCAO_FALHOU` no `REGISTRO.md`, deixar o
   item onde está e manter a trilha coerente. Sem retry cego — não existe
   "pedir permissão e tentar de novo".

No próximo briefing, usar `_processed.json` para não reapresentar como novo o
que já foi processado.

### Regras do destino de quarentena

1. `<escopo>` deste fluxo é `inbox` (a `higiene` usa `higiene`).
2. **Nunca sobrescrever**: antes de mover, checar o path candidato DIRETO
   (nunca listar `_to_delete/`); colisão de nome ganha sufixo determinístico
   (`-2`, `-3`, …).
3. **Retry idempotente**: item já no destino com o mesmo conteúdo → não criar
   cópia; só completar a trilha ou a baixa que faltou.
4. Symlink move-se como **link**; nunca seguir o alvo.
5. `_to_delete/` é **quarentena do usuário**: o Prumo nunca lista, indexa,
   conta ou esvazia (`file-protection-rules.md`). Não é `Arquivo/` nem o
   archive do runtime — não participa de `ARCHIVE-INDEX`.

### Sequência de arquivamento (retenção)

Arquivar é **mover o arquivo pro destino e editar depois, no lugar** — nunca
"escrever cópia nova no destino e apagar a velha": falha no meio deixa o
arquivo duplicado em dois diretórios (caso real de 27/07).

## Contrato mínimo do `_processed.json`

Formato recomendado:

```json
{
  "version": "1.0",
  "items": [
    {
      "filename": "captura-exemplo.txt",
      "processed_at": "2026-03-16T19:00:00-03:00",
      "status": "processed",
      "reason": "movido para quarentena"
    }
  ]
}
```

Regras:

1. O nome do arquivo deve ser preservado em `filename`.
2. `processed_at` deve registrar o timestamp ISO da decisão.
3. `status` recomendado: `processed`.
4. `reason` recomendado: `movido para quarentena` (ou o destino durável). O
   valor legado `fallback sem deleção física` continua válido em registros
   antigos — não reescrever histórico.
5. A limpeza fria da faxina só pode podar do JSON entrada marcada aqui, fria
   pelo threshold e cujo arquivo já saiu da pasta (#212).

## Material de referência

Quando o item for referência, **oferecer** a catalogação (nunca criar no escuro)
seguindo o template de `../ficha-de-fonte.md`:

1. **Motivo obrigatório** (`keep_with_reason`): se o porquê não for inferível do
   contexto, perguntar — uma pergunta curta. Sem motivo, não vira referência.
2. **Dois caminhos, conforme onde o conteúdo mora:**
   - conteúdo que o usuário quer **dentro** do workspace (arquivo trazido no
     inbox): mover para `Referencias/` e renomear com padrão descritivo, como
     sempre;
   - conteúdo que **mora fora** (URL, vault do usuário, drive): criar
     **ficha-ponteiro** em `Referencias/` apontando pra onde mora — catalogar,
     não armazenar; nunca copiar conteúdo externo sem pedido explícito.
   - texto do próprio usuário: mesma ficha, `Tipo: texto próprio`, apontando
     pra onde o texto vive.
3. registrar no `Referencias/INDICE.md` (mapeamento definido na
   `ficha-de-fonte.md`);
4. dar baixa no original conforme a máquina de remoção: arquivo **movido**
   pra `Referencias/` é retenção durável (já saiu do inbox — sem quarentena);
   ficha-ponteiro deixa o original materializado na ficha → o original vai
   pra quarentena, pelo fluxo normal de commit com `REGISTRO.md`.

## Destilação de ideias

Quando o item da triagem for **ideia** (sem próxima ação concreta — regra 5 do
core), aplicar no **processamento** — nunca na captura; o INBOX continua porta
de baixa fricção:

1. **Título-afirmação (oferta):** propor um título que **afirme a tese** da
   ideia — "Sistemas vencem disciplina quando o gatilho é ambiental" em vez de
   "pensar sobre hábitos". Ideia com tese fica localizável e combinável. Sempre
   como oferta com alternativas (regra 15); fragmento sem tese real continua
   válido como fragmento — não forçar afirmação onde não há.

2. **Duas ideias num item, dividir:** item que carrega duas ideias vira dois
   itens na triagem. Devolver UMA pergunta curta ao usuário só quando a divisão
   for genuinamente ambígua.

3. **Adensar sob demanda:** quando o usuário sinalizar "isso tem a ver com X"
   (ou o agente perceber no processamento e **oferecer**), o pensamento novo
   entra como **sub-bullet datado indentado sob o bullet-pai** da ideia
   existente em `IDEIAS.md`. A indentação é contrato, não estilo — é ela que
   faz o `acervo` capturar o adensamento como parte do item (contrato de
   fragmento: bullet + linhas indentadas):

   ```markdown
   - **Sistemas vencem disciplina quando o gatilho é ambiental.** (desde 20/06)
     - 01/07: contra-evidência — na viagem, sem ambiente controlado, o hábito caiu.
   ```

   Freios:

   - **Na dúvida, criar item separado** — fusão errada é pior que duplicação.
   - **Nenhuma varredura automática** de parentesco por item processado (a
     busca associativa pesada é da revisão semanal). O adensamento nasce de
     sinal do usuário ou de percepção incidental — nunca de scan.
   - Nenhuma rotina automática poda os sub-bullets datados; se um dia precisar
     de poda, é a `higiene` (que conversa).
   - Efeito no `acervo` (correto e desejado): adensar muda o `content_hash` do
     item; relatório antigo do acervo fica **bloqueado para delete** daquele
     item (hash divergente → pede revisão). É proteção, não bug.

## Regras de apresentação

1. Numerar os itens ao apresentar.
2. Oferecer alternativas de categorização quando houver ambiguidade.
3. Se sobrar item no inbox depois do commit, listar os remanescentes e dizer por quê.
