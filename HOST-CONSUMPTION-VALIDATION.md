# Protocolo de Validacao de Consumo por Host

Este documento existe para testar uma coisa simples e extremamente facil de estragar: se o host consome o contrato estruturado do Prumo como contrato, ou se volta a usar o JSON como desculpa para pescar prosa.

## Objetivo

Validar, em host real, que `prumo start --format json` e `prumo briefing --format json` ja carregam estrutura suficiente para:

1. guiar o fluxo sem parsing de string;
2. respeitar `next_move` e `selection_contract`;
3. lidar com degradacao parcial sem virar recepcionista em pânico;
4. evitar tool-chaining burocratico.

## Ordem correta de leitura

Ao consumir o payload estruturado, o host deve seguir esta ordem:

1. `degradation`
2. `next_move`
3. `selection_contract`
4. `state_flags`
5. `actions[]`
6. `google_status` e `integration_status`
7. `message` e `sections`, apenas para acabamento humano

Se o host inverter isso e comecar pela prosa, a validacao ja falhou.

## Cenarios minimos

### Cenario 0. Workspace legado sem identidade canônica

Esperado:

1. o host reconhece que `start` ainda nao e a primeira acao valida;
2. o host prioriza `migrate` antes de `start` ou `briefing`;
3. o host nao improvisa leitura de arquivo ou escrita em `_state/` para contornar a ausencia de identidade canonica;
4. depois de `migrate`, o host volta ao contrato normal e so entao executa `start` ou `briefing`.

### Cenario 1. Workspace quebrado

Esperado:

1. `degradation.status = error`
2. alerta principal aponta para `repair`
3. o host nao tenta briefing, onboarding ou coaching motivacional
4. a resposta humana e curta e centrada em recuperacao

### Cenario 2. Inicio do dia sem briefing

Esperado:

1. `next_move.id = briefing`
2. `selection_contract` deixa claro que aceite curto executa briefing
3. o host nao abre menu novo antes de oferecer ou executar o proximo movimento

### Cenario 3. Dia ja aberto com frente quente

Esperado:

1. `next_move.id = continue`
2. o host privilegia continuidade sobre briefing repetido
3. `message` serve para acabamento, nao para inverter a decisao do payload

### Cenario 4. Integracao parcial

Esperado:

1. `degradation.status = partial`
2. o host preserva o que ainda funciona
3. `google_status` e `integration_status` entram como estado operacional, nao como drama central

## Sinais de consumo ruim

A validacao falha quando o host:

1. le o `message` antes do payload operacional;
2. reroda `start` depois de aceite curto;
3. ignora `degradation` e segue como se nada tivesse acontecido;
4. concatena a propria liturgia com a prosa do runtime e vira duplicata de cartorio;
5. executa comando extra por ansiedade;
6. usa `google_status` ou `integration_status` para decidir fluxo que deveria sair de `state_flags` e `next_move`.

## Resultado minimo aceitavel

Um host passa quando:

1. usa `next_move` de forma disciplinada;
2. trata `selection_contract` como regra, nao como sugestao decorativa;
3. responde a degradacao sem melodrama nem negacao;
4. nao exige parsing textual para saber o que fazer;
5. nao introduz passos extras sem necessidade;
6. quando o workspace ainda e legado, nao pula `migrate` como se adocao canonica fosse opcional.

## Regra de bolso

Se a revisao do host precisar citar o `message` antes de citar `degradation`, `next_move` ou `selection_contract`, provavelmente o adapter ainda esta dirigindo olhando pelo retrovisor.
