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

**Verificar:**
- Listar arquivos em `Referencias/` (ignorar os operacionais: INDICE.md, WORKFLOWS.md, EMAIL-CURADORIA.md — mesma lista de exclusão do acervo)
- Comparar com a tabela em INDICE.md

**Executar se houver diferença:**
- Adicionar arquivos novos à tabela com: #, título (do cabeçalho), arquivo, data, descrição, keywords. **O `#` vem da alocação de ID do `ficha-de-fonte.md` (#244)** — rodapé `proximo-id` + sonda do candidato, sob lock atômico; nunca chutar pelo que a leitura parcial mostrou
- Ficha de fonte (ver `ficha-de-fonte.md` nas references do core): título = cabeçalho da ficha; data = campo Entrada; descrição = "Por que guardei" resumido; keywords = campo Keywords
- Se a tabela passar de `referencias_subcategorize_at` (default 30): agrupar por tema e criar seções

**Não fazer:**
- Não remover entradas cujo arquivo sumiu (pode ter sido movido)
  — marcar como "(arquivo não encontrado)" e deixar a higiene decidir

**Reportar:** "INDICE.md atualizado com X referência(s) nova(s)."

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
