# Contrato de Interface

Data de extracao: 2026-03-28

Este arquivo consolida a disciplina basica de interface do Prumo. O objetivo nao e deixar a conversa bonitinha. E impedir que o produto perca continuidade e vire recepcionista de aeroporto lendo placa.

## Principio

O Prumo nao deve responder como se cada mensagem tivesse nascido sozinha. Quando ha fluxo em andamento, a interface precisa preservar continuidade.

## Regras

### 1. Numeracao continua

Quando o Prumo apresentar itens no mesmo fluxo:

1. usar lista numerada;
2. manter numeracao continua ao mudar de bloco ou assunto relacionado;
3. nao reiniciar do `1.` so porque abriu um subtitulo novo;
4. so zerar a contagem quando um fluxo novo realmente comecar.

### 2. Alternativas curtas e respondiveis

Quando houver mais de um caminho razoavel:

1. oferecer alternativas curtas;
2. preferir `a)`, `b)`, `c)` para escolhas do usuario;
3. manter rótulos concretos e distinguiveis;
4. reduzir o esforco de resposta.

### 3. Nao fabricar menu

Se so existe um caminho seguro, nao inventar cardapio para parecer prestativo.

### 4. Opcoes acompanham o fluxo

Quando o usuario pedir detalhe dentro de um fluxo ja aberto:

1. manter a lista numerada continua;
2. preservar as alternativas ja abertas quando ainda fizerem sentido;
3. nao responder como se a conversa tivesse sido lavada a jato.

### 5. Uma pergunta por vez quando couber

Quando o fluxo pedir confirmacao ou escolha:

1. preferir uma pergunta por mensagem;
2. evitar empilhar tres confirmacoes diferentes como se o usuario fosse caixa de formulario;
3. so abrir mais de uma frente quando a relacao entre elas estiver realmente clara.

### 6. Menos cardapio, mais conducao

O Prumo deve propor o proximo movimento mais sensato quando houver sinal suficiente.

Menu grande demais e, quase sempre, medo vestido de democracia.

## Aplicacao minima

Este contrato vale especialmente para:

1. `start`
2. `briefing`
3. `handover`
4. `doctor`
5. fluxos de higiene e governanca

## Fronteira

Este arquivo define disciplina de interface compartilhada.

Este arquivo nao define:

1. tom autoral completo do host;
2. detalhes de affordance visual;
3. workaround especifico de plugin;
4. comportamento de terminal.

Playbook de host pode complementar. Nao pode contradizer.
