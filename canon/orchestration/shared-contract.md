# Contrato de Orquestracao Compartilhada

Data de extracao: 2026-03-28

Este arquivo define quem decide a sequencia do produto e ate onde essa decisao vai. Sem isso, cada host vira roteirista do proprio Prumo e a consistencia vira lenda urbana.

## Principio

O host nao deve reinventar o fluxo inteiro.
O runtime nao deve voltar a narrar a experiencia inteira.

A orquestracao compartilhada existe para decidir:

1. qual frente entra primeiro;
2. quando uma frente sobe ou desce;
3. qual acao vira proximo movimento recomendado;
4. qual o minimo de documentacao que acompanha a execucao.

## O que este contrato decide

### 1. Ordem macro de operacao

O contrato decide a precedencia entre:

1. `repair`
2. `align-core`
3. `briefing`
4. `continue`
5. `process-inbox`
6. `organize-day`
7. `auth-*`
8. `context`

### 2. Criterios de subida

O contrato decide quando:

1. `repair` entra antes de qualquer produtividade;
2. `briefing` entra antes de `continue`;
3. `continue` vence `briefing`;
4. `process-inbox` sobe;
5. `organize-day` vira default;
6. autenticacao entra como acao secundaria e nao como sequestro da manha.

### 3. Forma do proximo movimento

O contrato decide:

1. que existe um `next_move`;
2. que ele tem `id`, `label`, `kind`, `command`;
3. que a resposta curta do usuario pode executar esse proximo movimento sem novo menu;
4. que a execucao precisa ser seguida de resultado e mudanca documental, nao de outro cerimonial.

### 4. Relacao com documentacao viva

Cada acao deve carregar, quando fizer sentido:

1. alvos documentais;
2. resultado esperado;
3. motivo de prioridade.

Isso impede que o host execute e depois finja amnesia sobre o que deveria ter sido registrado.

## O que este contrato nao decide

1. o texto final exato que cada host escreve;
2. o tom completo da persona;
3. como cada host renderiza a UI;
4. shell path especifico;
5. detalhes de integracao por provider.

## Estados-base do dia

Hoje, o runtime ja trabalha com estes sinais:

1. estrutura quebrada (`missing generated/derived`) ;
2. core defasado;
3. briefing ainda nao rodado hoje;
4. existe item quente em andamento;
5. inbox encostada;
6. integracao Google desconectada;
7. diagnostico tecnico pedido explicitamente.

Esses sinais devem continuar sendo a materia-prima da orquestracao compartilhada.

## Regras de precedencia

### Regra 1. Estrutura primeiro

Se a estrutura esta quebrada, `repair` sobe para o topo.

Produto diario em workspace torto e igual correr maratona de chinelo. Pode ate acontecer. So nao chame isso de estrategia.

### Regra 2. Core desalinhado e urgencia de segunda camada

`align-core` nao sequestra a manha por reflexo.

Ele sobe quando:

1. o drift e detectado;
2. existe risco real de comportamento fantasma;
3. mas ainda assim fica abaixo de `repair` e pode ficar abaixo do trabalho quente dependendo do contexto do host.

### Regra 3. Sem briefing hoje, briefing tende a vencer

Se ainda nao houve briefing no dia:

1. `briefing` tende a ser o proximo movimento;
2. a excecao e estrutura quebrada.

### Regra 4. Trabalho quente vence briefing repetido

Se ja houve briefing hoje e existe item quente:

1. `continue` tende a subir acima de `briefing`;
2. o briefing repetido vira reabertura de radar, nao campainha default.

### Regra 5. Inbox sobe quando encostou, nao quando existe em tese

`process-inbox` sobe quando a fila esta real e relevante.

Nao porque inbox e um conceito bonito. Porque fila apodrece.

### Regra 6. Organizar o dia e o fallback honesto

Quando nao ha item quente claro nem inbox relevante:

1. `organize-day` vira acao default;
2. `briefing` continua disponivel;
3. o host nao precisa fabricar drama.

### Regra 7. Diagnostico nao entra por vaidade

`context` e diagnostico:

1. deve ficar disponivel;
2. nao deve subir por narcisismo tecnico;
3. entra quando ha duvida real ou pedido explicito.

## Contrato com o host

O host deve:

1. consumir a lista ordenada de acoes;
2. respeitar o `recommended`;
3. executar `next_move` quando o usuario responder curto;
4. nao rerodar o ritual inteiro so para se sentir participativo;
5. reportar resultado e mudancas documentais antes de oferecer nova rodada.

O host pode:

1. condensar prosa;
2. ajustar o tom;
3. escolher o quanto mostrar da lista;
4. adaptar apresentacao ao ambiente.

O host nao pode:

1. reordenar a lista inteira por gosto;
2. ignorar `repair` e `continue` quando claramente prioritarios;
3. transformar o contrato em mera sugestao decorativa.

## Relação com granularidade

Este contrato precisa ser consumivel sem procissao de micro-tool-calls.

Por isso, a orquestracao deve preferir:

1. acoes compostas com utilidade real de produto;
2. payloads estruturados suficientemente ricos;
3. fronteira clara entre decisao de fluxo e execucao tecnica fina.

Se cada passo exigir 6 chamadas para montar uma decisao banal, o contrato fica bonito e a UX morre no corredor.

## Implementacao atual de referencia

Hoje, a referencia viva desta logica esta em:

1. `runtime/prumo_runtime/daily_operator.py`
2. `runtime/prumo_runtime/commands/start.py`
3. `runtime/prumo_runtime/commands/briefing.py`

O objetivo futuro nao e jogar essa logica fora.
E fazer com que ela pare de morar como sabedoria implicita de arquivo Python.
