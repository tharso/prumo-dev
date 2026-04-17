---
name: faxina
description: >
  Faxina automática do workspace. Arquiva registro velho, atualiza índices,
  limpa inbox processado, move itens concluídos. Use com /faxina, "limpar",
  "organizar arquivos", "arquivar registro", ou quando o briefing detectar
  que algum arquivo está ficando pesado. Também roda silenciosamente no
  início de cada briefing para manter a casa em ordem.
---

# Faxina

A faxina cuida da casa sem incomodar. Ela não mexe no que é pessoal —
só organiza, arquiva e indexa.

Se o assunto precisa de decisão do usuário, não é faxina. É higiene.
A higiene conversa. A faxina age.

## Quando rodar

- **No briefing:** antes de apresentar qualquer coisa, checar se tem faxina pendente
- **Sob demanda:** `/faxina` ou "limpa os arquivos pra mim"
- **Nunca:** no meio de uma conversa produtiva (a faxina espera)

## O que a faxina faz

### 1. Rotação do REGISTRO.md

O registro é a trilha de tudo que aconteceu. Mas trilha acumulada vira
lama, não pavimento.

**Verificar:**
- Contar linhas na tabela de `REGISTRO.md`
- Se > 50 itens: hora de arquivar

**Executar:**
- Agrupar itens com mais de 30 dias por mês
- Mover pra `Prumo/Arquivo/REGISTRO-{yyyy-mm}.md`
- Manter os 50 mais recentes no arquivo principal
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

### 3. Agente/INDEX.md — atualização automática

O INDEX.md é o mapa de onde cada tipo de informação mora. Se alguém
criou um arquivo novo em `Agente/` ou deletou um antigo, o índice
precisa refletir isso.

**Verificar:**
- Listar arquivos em `Agente/`
- Comparar com o que está no INDEX.md

**Executar se houver diferença:**
- Atualizar a seção "Onde procurar o quê" com a lista atual
- Para cada arquivo: nome, descrição curta (inferida do cabeçalho), última modificação
- Manter o formato existente do INDEX.md

**Não fazer:**
- Não reescrever seções que não são sobre a lista de arquivos
- Não inventar descrições — usar o cabeçalho do arquivo como base

**Reportar:** "INDEX.md atualizado. {N} arquivo(s) novo(s), {M} removido(s)."

### 4. Referencias/INDICE.md — catálogo atualizado

A biblioteca de referências precisa de índice. Sem índice, o usuário
pergunta "onde guardei aquele artigo?" e Prumo não sabe.

**Verificar:**
- Listar arquivos em `Referencias/` (ignorar INDICE.md e WORKFLOWS.md)
- Comparar com a tabela em INDICE.md

**Executar se houver diferença:**
- Adicionar arquivos novos à tabela com: #, título (do cabeçalho), arquivo, data, descrição, keywords
- Se > 30 itens na tabela: agrupar por tema e criar seções

**Não fazer:**
- Não remover entradas cujo arquivo sumiu (pode ter sido movido)
  — marcar como "(arquivo não encontrado)" e deixar a higiene decidir

**Reportar:** "INDICE.md atualizado com X referência(s) nova(s)."

### 5. Inbox4Mobile — limpeza de processados

Itens que já foram processados e estão no `_processed.json` há mais
de 14 dias são lixo residual.

**Verificar:**
- Ler `_processed.json`
- Filtrar entradas com `processed_at` > 14 dias atrás

**Executar:**
- Remover essas entradas do JSON
- Se o arquivo original ainda existir e estiver como "processed": pode
  mover pra `Prumo/Arquivo/` (sem deletar)

**Reportar:** "Limpei X entrada(s) antiga(s) do inbox processado."

## Relatório da faxina

Depois de rodar tudo, montar um resumo curto. Exemplo:

> Faxina feita.
> - Registro: arquivei 23 itens antigos (jan–fev)
> - Pauta: movi 3 itens concluídos pro registro
> - INDEX.md: atualizado (1 arquivo novo)
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
