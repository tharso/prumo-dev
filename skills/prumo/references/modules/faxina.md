# Faxina (módulo do core)

> Era a skill top-level `faxina` até a 5.31 — a #172 tirou a mecânica do
> picker. Nada muda no comportamento: roda no início do briefing e no `/fim`
> (automática), ou a pedido em linguagem natural ("limpa os arquivos",
> "organizar arquivos", "arquivar registro").

A faxina cuida da casa sem incomodar. Ela não mexe no que é pessoal —
só organiza, arquiva e indexa.

Se o assunto precisa de decisão do usuário, não é faxina. É higiene.
A higiene conversa. A faxina age.

## Quando rodar

- **No briefing:** antes de apresentar qualquer coisa, checar se tem faxina pendente
- **Sob demanda:** "limpa os arquivos pra mim", "organizar arquivos"
- **Nunca:** no meio de uma conversa produtiva (a faxina espera)

> **Origem dos números (#258):** com semente, os efetivos vêm em `faxina.thresholds` (override já aplicado). Sem semente, com schema desconhecido ou override divergente: defaults do `faxina-thresholds.md` **+ o override em `Custom/rules/`** — ignorá-lo é checar contra a configuração do usuário.

## O que a faxina faz

### 1. Rotação do REGISTRO.md

O registro é a trilha de tudo que aconteceu. Mas trilha acumulada vira
lama, não pavimento.

**Verificar:**
- Contar linhas na tabela de `REGISTRO.md`
- Se acima de `max_items` (default 50 — `faxina-thresholds.md`; overrides em `Prumo/Custom/rules/`): hora de arquivar

**Executar:**
- Agrupar itens além de `archive_age_days` (default 30) por mês
- Mover pra `Prumo/Arquivo/REGISTRO-{yyyy-mm}.md`
- Manter os `max_items` mais recentes no arquivo principal
- Adicionar nota no cabeçalho: "Itens anteriores em `Arquivo/`"

**Não fazer:**
- Não deletar nenhum item — mover é diferente de apagar
- Não reformatar a tabela — mover as linhas como estão

**Reportar:** "Arquivei X itens antigos do registro. O mais velho era de {mês}."

### 2. PAUTA.md → REGISTRO.md

Itens concluídos na pauta não precisam ficar lá. A pauta é o que está
vivo. O registro é a trilha.

**Verificar:**
- Procurar itens marcados como concluídos (checkbox marcado, texto
  riscado, ou explicitamente movido para "Concluído")

**Executar:**
- Mover pra REGISTRO.md com data de conclusão
- Formato: `| {data} | PAUTA | {resumo do item} | Concluído | REGISTRO |`
- Remover da PAUTA.md

**Não fazer:**
- Não mover itens que não estejam explicitamente concluídos
- Não interpretar "hibernando" como concluído

**Reportar:** "Movi X itens concluídos da pauta pro registro."

### 3. Referencias/INDICE.md — catálogo atualizado

A biblioteca de referências precisa de índice. Sem índice, o usuário
pergunta "onde guardei aquele artigo?" e Prumo não sabe.

**Verificar (uma leitura, uma decisão — com semente, tudo já vem pronto em
`local_panorama.indice_referencias`):**
- Rodapé `<!-- proximo-id: N -->` e os IDs distintos da tabela
- Arquivos em `Referencias/` (ignorar os operacionais: INDICE.md, WORKFLOWS.md, EMAIL-CURADORIA.md — mesma lista de exclusão do acervo), comparados com a tabela

**Decidir nesta ordem, e parar na primeira que bater:**

0. **Índice ausente com ficha em disco (#261).** `INDICE.md` não existe e há
   ficha em `Referencias/`: **não criar o índice**. Recriá-lo daria IDs novos e
   descrições derivadas — é a forma mais grave do incidente, não workspace
   novo. Pasta sem índice E sem ficha é começo: segue limpo.
1. **Lacuna de ID (#261).** Com rodapé presente e `N > 1`: `slots = N-1`;
   `ocupados` = IDs distintos em `1..slots` (ID ≥ N não preenche lacuna — o
   rodapé é sugestão e pode estar atrasado; duplicata conta uma vez). Se
   `lacunas × 100 ≥ referencias_id_gap_alert_pct × slots` (default 50 —
   comparar TAXA, nunca a contagem crua): **não alterar o índice**, relatar e entregar pra higiene. Sem rodapé, ou malformado, este
   passo é PULADO — ausência de rodapé nunca é alarme por si. Lacuna já
   declarada deliberada (`<!-- lacunas-conferidas: L/S -->`, fração exata) não
   volta a alarmar: só o que CRESCEU além dela conta — comparar por
   `lacunas × S > L × slots` (igualdade NÃO é crescimento). Marca só vale com `0 < S` e `0 ≤ L ≤ S`:
   fração impossível (`999/1`, `0/0`) é ignorada, nunca silencia.
2. **Volume (#261).** Se as fichas fora da tabela forem `≥ referencias_bulk_reindex_at`
   (default 5): **não alterar o índice**, relatar e entregar pra higiene.
   N fichas fora do índice de uma vez não são "N fichas novas" — são um
   estado que precisa de explicação. Ficha já declarada deliberada
   (`<!-- fichas-fora-conferidas: a.md, b.md -->`) sai da conta: a marca é
   por NOME, então a ficha nova de amanhã continua sendo indexada.
3. **Reindexar.** Abaixo dos dois limiares: adicionar as fichas novas à
   tabela **nomeando cada uma** no relato. O `#` vem da alocação de ID do
   `ficha-de-fonte.md` (#244) — rodapé `proximo-id` + sonda do candidato, sob
   lock atômico; nunca chutar pelo que a leitura parcial mostrou.
   - Ficha de fonte (ver `ficha-de-fonte.md`): título = cabeçalho da ficha;
     data = campo Entrada; descrição = "Por que guardei" resumido;
     keywords = campo Keywords
   - Se a tabela passar de `referencias_subcategorize_at` (default 30):
     agrupar por tema e criar seções. Reagrupar é **reescrita integral** —
     segue `escrita-curada.md` (lock adquirido durante a janela inteira, ler
     tudo antes, preservar toda linha, ID e descrição).

**Por que bloquear em vez de consertar:** até a #261 esta seção mandava
adicionar o que faltasse, sem teto e em silêncio. Depois do truncamento de
27/07 (48 entradas viraram 5), qualquer briefing dos dois dias seguintes teria
reinserido 37 fichas com **IDs novos**, trocado as descrições autorais pelas
derivadas do "Por que guardei" e reportado sucesso. É a salvaguarda da #212
aplicada aqui: estado inconsistente sinaliza e para.

**Não fazer:**
- Não remover entradas cujo arquivo sumiu (pode ter sido movido)
  — marcar como "(arquivo não encontrado)" e deixar a higiene decidir
- Não "consertar" índice suspeito. Bloqueio é o conserto.
- Não emitir dois avisos pro mesmo estado: quando o passo 1 bloqueia, a
  contagem de fichas fora entra como **evidência** na mesma linha, não como
  segundo alarme.

**Reportar:**
- Bloqueado: "Índice de referências inconsistente — {razões}. Não alterei o
  índice; leve pra higiene." Nomear as fichas fora da tabela. Diga **suspeito**,
  nunca "dano confirmado": nenhuma porcentagem lê intenção, e apagar uma seção
  de propósito produz o mesmo observável.
- Reindexado: "INDICE.md atualizado com: `a.md`, `b.md`." Nomear, não só contar
  — perda de UMA linha é indistinguível de ficha nova pela diferença de
  conjuntos, mas trivial pro usuário, que é o único que sabe que aquilo é de
  fevereiro.

### 4. Inbox4Mobile — limpeza de processados

Itens que já foram processados e estão no `_processed.json` além de
`processed_expiry_days` (default 14) são lixo residual.

**Verificar:**
- Ler `_processed.json`
- Filtrar entradas com `processed_at` além de `processed_expiry_days`
- **Salvaguarda (#212): nunca remover entrada cujo arquivo ainda existe em `Inbox4Mobile/`** — `processed_at` velho com o arquivo ainda na pasta é estado inconsistente (o item talvez NÃO tenha sido processado de verdade): sinalizar ao usuário em vez de podar. A poda é por IDADE; a orfandade é só a trava de segurança — no dado real de 25/07, 0 das 43 entradas eram removíveis pelo critério de orfandade (as "órfãs" aparentes estavam legitimamente no `Arquivo/`).

**Executar:**
- Remover do JSON apenas as entradas velhas cujo arquivo **não** está mais
  em `Inbox4Mobile/` (já arquivado ou removido pelo fluxo normal).
- **Arquivo ainda presente → não mover, não podar; apenas sinalizar** (a
  salvaguarda da #212 acima): estado inconsistente é decisão do usuário,
  nunca da faxina. A resolução assistida — oferecer mover esses arquivos pra
  quarentena `_to_delete/`, com confirmação — mora na `higiene` (#242).

**Reportar:** "Limpei X entrada(s) antiga(s) do inbox processado." — e, se houver, "Y entrada(s) inconsistente(s) sinalizadas (processadas no JSON, mas com arquivo ainda na pasta)."

### 5. Diario/ — rotação por data

O diário (gerado pelo `/fim`) é fechado por data: cada arquivo é a
fotografia de um dia. Fotografia não apodrece, mas pilha de fotografia
vira entulho na mesa.

**Verificar:**
- Listar `Prumo/Diario/*.md` cuja data no **nome** do arquivo (AAAA-MM-DD)
  passe de `diario_expiry_days` (default 90)

**Executar:**
- Mover pra `Prumo/Arquivo/Diario/` (mover, nunca apagar)

**Não fazer:**
- Não ler o conteúdo dos diários — a idade vem do nome do arquivo
  (faxina nunca decide o que é importante)
- Não tocar no diário de hoje

**Reportar:** "Arquivei X diário(s) além do prazo de rotação."

## Relatório da faxina

Depois de rodar tudo, montar um resumo curto. Exemplo:

> Faxina feita.
> - Registro: arquivei 23 itens antigos (jan–fev)
> - Pauta: movi 3 itens concluídos pro registro
> - Inbox: limpei 5 entradas processadas
>
> Nada mais precisava de atenção.

Se nada precisou de faxina: "Casa em ordem. Nada pra limpar."

## O que a faxina nunca faz

1. **Faxina nunca deleta conteúdo do usuário.** Mover é diferente de apagar.
2. **Faxina nunca decide o que é importante.** Ela move por idade e status, não por julgamento.
3. **Faxina não conversa.** Se precisa de decisão, registra o achado e deixa pra higiene.
4. **Faxina preserva Custom/.** Nunca toca em `Prumo/Custom/`.
5. **Faxina roda rápido.** Se tem muita coisa, faz o principal e anota o resto.

## Relação com outras skills

- **higiene** — o que a faxina detecta mas não pode resolver sozinha vai pra higiene
- **sanitize** — faxina cuida de arquivos do usuário; sanitize cuida de `.prumo/` (sistema)
- **briefing** — a faxina roda antes do briefing pra manter a casa limpa
