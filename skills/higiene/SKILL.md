---
name: higiene
description: >
  Higiene assistida do workspace. Detecta problemas que precisam de decisão
  do usuário: itens velhos na pauta, contradições entre arquivos, CLAUDE.md
  pesado, contexto obsoleto em Agente/, inbox esquecido, referências quebradas,
  órfãos e índice de referências inconsistente. Propõe e espera
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

## Voz das propostas

A VOZ das propostas vem de `Prumo/Agente/PERFIL.md` — o tom que o usuário
configurou (Direto, Equilibrado, Gentil ou o dele próprio). Cada detecção abaixo
declara a **Intenção** (o que comunicar); o exemplo é ilustração numa voz,
**nunca script pra repetir** — seis sessões com a mesma frase decorada é
telemarketing, não parceria.

## O que a higiene detecta

### 1. PERFIL.md pesado ou bagunçado

Isso já existia e continua funcionando.

**Verificar:**
- Duplicações, redundâncias, conflitos dentro do PERFIL.md
- Conteúdo que deveria estar em outro arquivo (pendências no PERFIL.md
  que pertencem à PAUTA.md, histórico que pertence ao REGISTRO.md)
- **Rituais recorrentes no PERFIL** (seção "Lembretes recorrentes", modelo
  legado anterior à 5.9) — devem migrar por natureza: com hora → agenda
  (oferecer criar, sem escrever sem o ok); sem hora → `Agente/ROTINA.md`;
  sem mudar nenhuma decisão → poda
- `.prumo/system/PRUMO-CORE.md` defasado em relação ao runtime

**Como funciona:**
- Ler `skills/prumo/references/modules/claude-hygiene.md` para o procedimento detalhado (o nome do módulo é histórico — cobre a higiene do `PERFIL.md` e dos módulos do `Agente/`)
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

**Intenção:** nomear o tempo parado com número concreto e devolver a decisão (reativar, limpar ou hibernar) — sem culpa e sem pressão.
Exemplo (voz Equilibrada — não é script): "Faz 18 dias que isso tá aqui. Se ainda importa, vamos reativar. Se não, tiro da frente."

### 3. Agente/ com informação possivelmente obsoleta

**Verificar:**
- Data de última modificação dos arquivos em `Agente/`
- Arquivos com mais de 6 meses sem alteração
- **`ROTINA.md` inflado ou redundante**: linhas que repetem a mesma rotina;
  histórico de ocorrências disfarçado ("segunda fiz X, terça fiz X" — o ROTINA
  guarda o *padrão* estável, não o log do que aconteceu); ritual com hora que
  deveria estar só na agenda (não duplicado no ROTINA); ou contexto que não
  muda nenhuma decisão do Prumo (candidato a poda)

**Propor (um arquivo por vez):**
- "PROJETOS.md tem 8 meses sem mexer. Ainda vale ou posso arquivar?"
- Se o usuário confirmar que vale: atualizar data de modificação (touch)
- Se confirmar que não vale: mover pra `Prumo/Arquivo/`

**Intenção:** perguntar vigência sem acusar erro — obsolescência é hipótese a confirmar, não veredito.
Exemplo (voz Equilibrada — não é script): "Não tô dizendo que tá errado. Só tô perguntando se ainda serve."

### 4. INBOX.md com itens esquecidos

**Verificar:**
- INBOX.md com itens há mais de 7 dias
- Inbox4Mobile com arquivos não processados
- Inbox4Mobile com **processados inconsistentes**: entrada no `_processed.json`
  além do threshold com o arquivo ainda na pasta (a faxina sinaliza e para —
  #212; a resolução é daqui)
- **Caixa declarada envelhecida (#245)**: pasta marcada `(caixa de entrada)` no
  mapa autoral com item mais velho que `declared_inbox_stale_days` (default 14
  — `faxina-thresholds.md`; overrides em `Prumo/Custom/rules/`). A idade vem do
  **mtime** (metadata rasa autorizada pelo contrato do marcador; conteúdo,
  nunca)

**Propor:**
- "Tem coisa no inbox há X dias. Quer processar agora ou deixar pra depois?"
- Se "agora": entrar no fluxo de inbox processing
- Se "depois": deixar, sem insistir
- Pros processados inconsistentes: "Tem N arquivo(s) marcados como processados
  que continuam na pasta. Movo pra quarentena `_to_delete/` pra você esvaziar
  quando quiser?" — só com confirmação explícita; mover segue a máquina de
  remoção do `inbox-processing.md` (escopo `higiene`, com trilha no REGISTRO)
- Pra caixa declarada envelhecida: "`X/` tem N itens, o mais velho de DD/MM.
  Quer processar agora ou deixar pra depois?" — sinalizar, nunca reorganizar
  sozinha

**Intenção:** alertar o custo de fila parada e entregar a escolha (agora ou depois) sem insistir.
Exemplo (voz Equilibrada — não é script): "Fila encostada tende a apodrecer. Mas a decisão é sua."

### 5. Contradições entre arquivos

**Verificar:**
- Item em PAUTA.md marcado como pendente que aparece como concluído em REGISTRO.md
- Dados conflitantes entre Agente/PESSOAS.md e PAUTA.md
- Informação que aparece em dois arquivos com versões diferentes

**Propor:**
- "Achei uma contradição: {arquivo A} diz X, {arquivo B} diz Y. Qual vale?"
- Apresentar os dois trechos
- Aplicar a correção no arquivo errado

**Intenção:** apresentar os dois lados sem arbitrar — quem sabe qual vale é o usuário.
Exemplo (voz Equilibrada — não é script): "Não sei qual tá certo. Você sabe."

### 6. Arquivos grandes demais

**Verificar:**
- AGENT.md ou `.prumo/system/PRUMO-CORE.md` > 500 linhas
- PAUTA.md > 200 linhas
- Qualquer arquivo em Agente/ > 300 linhas

**Propor:**
- "A pauta tá com {N} linhas. Quer mover o que tá hibernando pra arquivo?"
- "AGENT.md tá pesado ({N} linhas). Quer revisar comigo?"
- Para Agente/: "PESSOAS.md tá grande. Quer separar por grupo?"

**Intenção:** explicar o custo concreto (contexto caro) e oferecer o alívio como convite, não como cobrança.
Exemplo (voz Equilibrada — não é script): "Arquivo pesado demais faz o contexto ficar caro. Vamos aliviar?"

### 7. Custom/ possivelmente incompatível

**Verificar:**
- Se `.prumo/system/skills/` foi atualizado recentemente
- Se `Prumo/Custom/skills/` tem overrides
- Comparar versões (data de modificação como proxy)

**Propor:**
- "O sistema atualizou e você tem um override do briefing. Pode ter ficado incompatível. Quer revisar?"

**Intenção:** avisar que a customização pode ter ficado para trás sem sugerir que ela foi um erro — override é escolha do usuário, não dívida.
Exemplo (voz Equilibrada — não é script): "Seu ajuste continua valendo. Só não sei se ele ainda encaixa na versão nova — quer conferir junto?"

### 8. Integridade referencial (órfãos e cross-refs quebradas)

O eixo que faltava. A higiene cobre contradição e staleness, mas não
**integridade referencial** — referência que aponta pra lugar nenhum, e coisa
mencionada que nunca ganhou página. Mesma natureza dos outros checks: detecta e
propõe, nunca conserta sozinha.

**Verificar** (só o que dá pra ver lendo o Markdown do workspace):
- **Tag sem área:** tag ou frente usada na `PAUTA.md` (ex.: `[Trabalho/Startup X]`)
  que não mapeia pra nenhuma área definida no `PERFIL.md`.
- **Pessoa órfã:** pessoa em `Agente/PESSOAS.md` sem nenhum item ativo que a
  referencie (nem na PAUTA, nem no INBOX, nem em item recente do REGISTRO).
- **Referência quebrada:** menção ou link a um arquivo (`Referencias/contrato.md`,
  um anexo, outro `.md`) que não existe mais no workspace.
- **Projeto/área sem página:** item que menciona um projeto ou área sem README
  ou arquivo correspondente onde ele deveria morar.

**Propor (uma decisão por vez):**
- Tag sem área: "A tag `X` aparece na pauta mas não existe no PERFIL. Criar a
  área, renomear a tag, ou foi engano?"
- Pessoa órfã: "`Fulano` está em PESSOAS mas não puxa nada ativo. Arquivar, ou
  ainda importa?"
- Referência quebrada: "A pauta aponta pra `Referencias/contrato.md`, que não
  existe mais. Corrigir o caminho, ou tirar a menção?"
- Projeto sem página: "Você cita o projeto `Y` mas não tem página dele. Criar,
  ou é só contexto solto?"

**Intenção:** apontar o alvo inexistente como observação com as duas saídas (arrumar ou deixar) — estilo pessoal nunca é erro.
Exemplo (voz Equilibrada — não é script): "Não tô dizendo que tá errado. Só reparei que isso aponta pra lugar nenhum — quer arrumar ou deixar?"

**Limite (anti-zelo):** ausência de convenção **não é erro**. Não exigir área pra
toda tag, README pra todo projeto, nem página pra toda pessoa se o usuário não
adotou esse estilo. Órfão de verdade é referência que aponta pra nada — não o
jeito pessoal de organizar. Na dúvida entre "quebrado" e "estilo", é estilo:
pergunta leve, sem acusar.

### 9. Integridade do índice de referências (#261)

A faxina detecta e **para**; a resolução é daqui. Ela bloqueia quando o
`Referencias/INDICE.md` fica suspeito — lacuna de ID acima de
`referencias_id_gap_alert_pct` ou fichas fora da tabela a partir de
`referencias_bulk_reindex_at`. **Use os números EFETIVOS**, não os defaults:
`faxina.thresholds` da semente (#258) ou, sem semente, `faxina-thresholds.md`
**mais** o override em `Prumo/Custom/rules/`. Com override mais sensível, a
faxina bloqueia e a higiene com default concluiria que não há problema — o
bombeiro chegando e discordando do alarme.

**Verificar (refazer a conta, não confiar na anterior):**
- Rodapé `<!-- proximo-id: N -->` × IDs distintos da tabela
- Fichas em `Referencias/` sem entrada, **nomeadas uma a uma**
- Cópia disponível em `.prumo/backups/curated/` (#262) — é ela que preserva os
  IDs e as descrições autorais originais

**Propor (uma decisão por vez, nenhuma escrita antes da escolha):**
- Com cópia: "Achei N ficha(s) fora do índice e o rodapé aponta pra um índice
  bem maior. Tem uma cópia de {data} com as entradas originais. Restauro a
  partir dela, preservando IDs e descrições?"
- Sem cópia: "Não tenho cópia anterior. Posso recriar as entradas a partir das
  fichas, mas os IDs serão novos e as descrições virão do 'Por que guardei' —
  as originais não voltam. Faço assim, ou você prefere reescrever à mão?"
- Sempre oferecer a terceira saída: **"a remoção foi deliberada"**. Nada é
  reinserido, e a higiene grava no índice as DUAS marcas do que foi aceito —
  `<!-- lacunas-conferidas: L/S -->` (fração exata, nunca percentual
  arredondado) e `<!-- fichas-fora-conferidas: a.md, b.md -->` (por NOME).
  É isso que faz a faxina parar de bloquear. Sem gravar, a confirmação não
  muda o estado observável e o mesmo alarme volta na rodada seguinte: saída
  cenográfica. Gravar só uma das duas também não fecha — a outra dimensão
  bloqueia em seguida. Só o que CRESCER além do aceito alarma de novo, e ficha
  nova continua sendo indexada normalmente.

**Intenção:** tratar como estado a explicar, não como erro a corrigir — nenhuma porcentagem lê intenção, e apagar uma seção de propósito produz o mesmo observável de um truncamento.
Exemplo (voz Equilibrada — não é script): "Isso aqui tá estranho, mas pode ser
coisa sua. O índice aponta pra 48 e mostra 4. Foi você que limpou, ou perdemos
alguma coisa?"

**Nunca:** reinserir automaticamente. Foi exatamente o reflexo automático que
teria cimentado o dano de 27/07.

## Fluxo de execução

1. Rodar todos os checks (1-9)
2. Se nada encontrado: "Casa em ordem. Nada pra revisar."
3. Se encontrou algo: apresentar lista curta dos achados
4. Perguntar: "Quer resolver agora ou coloco na pauta pra depois?"
5. Se agora: uma decisão por vez, na ordem de urgência
6. Se depois: adicionar como item na PAUTA.md seção "Quente"

## O que a higiene nunca faz sozinha

1. **Higiene nunca resolve sozinha.** Sempre propõe, sempre espera.
2. **Uma decisão por vez.** Não empilhar 7 perguntas numa mensagem.
3. **Backup antes de mudar.** Se vai editar PERFIL.md ou mover arquivo, backup primeiro. **Exceção (#242):** mover pra quarentena `_to_delete/` é, por si, a operação recuperável — não recebe backup duplicado.
4. **Registrar em REGISTRO.md.** Toda mudança aplicada vira linha no registro.
5. **Nunca reescrever preferências subjetivas.** Se o usuário escreveu de um jeito, é de um jeito.
6. **Custom/ é sagrado.** Não propor mudanças em Custom/ — só avisar incompatibilidade.

## Relação com outras skills

- **faxina** — o que não precisa de decisão vai pra faxina
- **briefing** — a higiene pode ser acionada pelo briefing quando detectar sinais
- **sanitize** — o sanitize cuida de estado técnico; a higiene cuida de conteúdo do usuário
