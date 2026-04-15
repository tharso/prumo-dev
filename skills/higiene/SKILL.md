---
name: higiene
description: >
  Higiene assistida do workspace. Detecta problemas que precisam de decisão
  do usuário: itens velhos na pauta, contradições entre arquivos, CLAUDE.md
  pesado, contexto obsoleto em Agente/, inbox esquecido. Propõe e espera
  confirmação — nunca resolve sozinha. Use com /higiene, "tem algo pra
  limpar?", "revisa meus arquivos", ou quando o briefing detectar sinais.
---

# Higiene

A higiene é parceria. Prumo detecta o problema e propõe saída.
A decisão é sempre do usuário.

Se o problema pode ser resolvido sem perguntar, não é higiene. É faxina.
A faxina age. A higiene conversa.

## Quando rodar

- **Sob demanda:** `/higiene` ou "tem algo pra limpar?"
- **No briefing:** quando detectar sinais, adiciona como item de pauta
  ("Achei umas coisas que podem estar atrapalhando. Quer resolver comigo?")
- **Nunca:** sem avisar — higiene sempre mostra o que encontrou antes de propor

## O que a higiene detecta

### 1. PERFIL.md pesado ou bagunçado

Isso já existia e continua funcionando.

**Verificar:**
- Duplicações, redundâncias, conflitos dentro do PERFIL.md
- Conteúdo que deveria estar em outro arquivo (pendências no PERFIL.md
  que pertencem à PAUTA.md, histórico que pertence ao REGISTRO.md)
- `.prumo/system/PRUMO-CORE.md` defasado em relação ao runtime

**Como funciona:**
- Ler `skills/prumo/references/modules/perfil-hygiene.md` para o procedimento detalhado
- Apresentar em 3 blocos fixos: mudanças seguras, confirmações factuais, decisões de governança
- Só aplicar com confirmação explícita

### 2. PAUTA.md com itens parados

**Verificar:**
- Itens com `(desde DD/MM)` onde a data tem mais de 14 dias
- Itens na seção "Quente" que nunca foram trabalhados
- Itens na seção "Em andamento" sem atividade recente

**Propor (uma decisão por vez):**
- "Tem X itens parados há mais de 2 semanas."
- Para cada item: "Quer limpar, reativar, ou mover pra Hibernando?"
- Se muitos itens (> 5): agrupar e perguntar em lote

**Tom:** "Faz 18 dias que isso tá aqui. Se ainda importa, vamos reativar. Se não, tiro da frente."

### 3. Agente/ com informação possivelmente obsoleta

**Verificar:**
- Data de última modificação dos arquivos em `Agente/`
- Arquivos com mais de 6 meses sem alteração

**Propor (um arquivo por vez):**
- "PROJETOS.md tem 8 meses sem mexer. Ainda vale ou posso arquivar?"
- Se o usuário confirmar que vale: atualizar data de modificação (touch)
- Se confirmar que não vale: mover pra `Prumo/Arquivo/`

**Tom:** "Não tô dizendo que tá errado. Só tô perguntando se ainda serve."

### 4. INBOX.md com itens esquecidos

**Verificar:**
- INBOX.md com itens há mais de 7 dias
- Inbox4Mobile com arquivos não processados

**Propor:**
- "Tem coisa no inbox há X dias. Quer processar agora ou deixar pra depois?"
- Se "agora": entrar no fluxo de inbox processing
- Se "depois": deixar, sem insistir

**Tom:** "Fila encostada tende a apodrecer. Mas a decisão é sua."

### 5. Contradições entre arquivos

**Verificar:**
- Item em PAUTA.md marcado como pendente que aparece como concluído em REGISTRO.md
- Dados conflitantes entre Agente/PESSOAS.md e PAUTA.md
- Informação que aparece em dois arquivos com versões diferentes

**Propor:**
- "Achei uma contradição: {arquivo A} diz X, {arquivo B} diz Y. Qual vale?"
- Apresentar os dois trechos
- Aplicar a correção no arquivo errado

**Tom:** "Não sei qual tá certo. Você sabe."

### 6. Arquivos grandes demais

**Verificar:**
- AGENT.md ou `.prumo/system/PRUMO-CORE.md` > 500 linhas
- PAUTA.md > 200 linhas
- Qualquer arquivo em Agente/ > 300 linhas

**Propor:**
- "A pauta tá com {N} linhas. Quer mover o que tá hibernando pra arquivo?"
- "AGENT.md tá pesado ({N} linhas). Quer revisar comigo?"
- Para Agente/: "PESSOAS.md tá grande. Quer separar por grupo?"

**Tom:** "Arquivo pesado demais faz o contexto ficar caro. Vamos aliviar?"

### 7. Custom/ possivelmente incompatível

**Verificar:**
- Se `.prumo/system/skills/` foi atualizado recentemente
- Se `Prumo/Custom/skills/` tem overrides
- Comparar versões (data de modificação como proxy)

**Propor:**
- "O sistema atualizou e você tem um override do briefing. Pode ter ficado incompatível. Quer revisar?"

## Fluxo de execução

1. Rodar todos os checks (1-7)
2. Se nada encontrado: "Casa em ordem. Nada pra revisar."
3. Se encontrou algo: apresentar lista curta dos achados
4. Perguntar: "Quer resolver agora ou coloco na pauta pra depois?"
5. Se agora: uma decisão por vez, na ordem de urgência
6. Se depois: adicionar como item na PAUTA.md seção "Quente"

## O que a higiene nunca faz sozinha

1. **Higiene nunca resolve sozinha.** Sempre propõe, sempre espera.
2. **Uma decisão por vez.** Não empilhar 7 perguntas numa mensagem.
3. **Backup antes de mudar.** Se vai editar PERFIL.md ou mover arquivo, backup primeiro.
4. **Registrar em REGISTRO.md.** Toda mudança aplicada vira linha no registro.
5. **Nunca reescrever preferências subjetivas.** Se o usuário escreveu de um jeito, é de um jeito.
6. **Custom/ é sagrado.** Não propor mudanças em Custom/ — só avisar incompatibilidade.

## Relação com outras skills

- **faxina** — o que não precisa de decisão vai pra faxina
- **briefing** — a higiene pode ser acionada pelo briefing quando detectar sinais
- **sanitize** — o sanitize cuida de estado técnico; a higiene cuida de conteúdo do usuário
