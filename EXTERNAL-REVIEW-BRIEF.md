# External Review Brief

## O que e isto

Este documento existe para pedir revisao externa do Prumo sem transformar a conversa em neblina.

O objetivo nao e perguntar "o que voce acha do projeto?".
O objetivo e forcar uma leitura critica sobre:

1. produto
2. arquitetura
3. contrato com hosts
4. gaps entre o legado plugin-first e o runtime atual
5. risco real do piloto comercial

## O que e o Prumo hoje

Prumo esta sendo reconstruido como runtime local-first.

Ele nao deve ser tratado como "um briefing esperto".
O valor esperado do produto nesta fase e:

1. entender o estado do dia
2. propor o proximo passo sensato
3. sustentar continuidade de trabalho
4. atualizar documentacao viva do workspace
5. preparar o terreno para workflows futuros

## Direcao da fase atual

1. `Antigravity` e o trilho principal do primeiro piloto comercial.
2. `Codex` e o host de referencia tecnica.
3. `Claude Code` segue suportado no modo shell-explicito.
4. `Cowork` ficou em backlog preparado.
5. `Gemini CLI` saiu do foco.
6. `Apple Reminders` ficou fora desta fase.
7. `Windows` entrou como requisito arquitetural minimo.

## Estado tecnico atual

Versao atual do runtime: `4.16.4`

Pontos importantes que ja entraram:

1. `prumo start --format json` e `prumo briefing --format json` expõem `next_move`.
2. O runtime agora expõe `selection_contract`, deixando explicito que respostas curtas como `1`, `a`, `aceitar`, `seguir` e `ok` devem executar `next_move` sem rerodar `start` nem devolver menu.
3. O runtime oferece `align-core` quando houver drift entre runtime e core do workspace.
4. Existe comando canônico `prumo inbox preview`.
5. O runtime passou a declarar `platform`, `capabilities`, `daily_operation`, `documentation_rules` e `conversation_rules`.
6. A estrutura para workflows existe, mas ainda sem workflow vertical fechado.

## O problema real da fase

O produto esta tecnicamente mais solido do que o legado.
Mas a experiencia ainda oscila entre duas personas:

1. operador diario que conduz trabalho real
2. recepcionista que mostra cardapio e pede confirmacao demais

Em portugues simples:
o produto ja tem esqueleto melhor, mas ainda precisa recuperar a fluidez percebida do plugin antigo sem voltar a depender do host antigo.

## O que queremos da revisao

Queremos critica dura, nao elogio educado.

Se o reviewer achar que estamos errando a mao, ele deve dizer:

1. onde a arquitetura esta certa, mas a UX esta torta
2. onde estamos sofisticando cedo demais
3. onde ainda estamos romantizando o legado
4. onde o piloto comercial corre risco por falta de polimento
5. o que falta para a experiencia parecer produto e nao demo instrumental

## Perguntas que importam

1. A direcao atual do Prumo esta correta ou ainda esta presa demais ao formato de briefing?
2. `next_move` + `selection_contract` + `actions[]` parecem contrato suficiente para host decente, ou ainda falta fechar buracos?
3. A documentacao viva (`PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `Referencias/WORKFLOWS.md`) esta virando parte do valor do produto ou ainda parece side effect?
4. O piloto via `Antigravity` parece comercialmente defensavel ou ainda esta com cheiro de laboratorio?
5. O que falta para recuperar a fluidez do legado sem reintroduzir o acoplamento do legado?
6. Quais sao os 3 riscos tecnicos e de produto mais subestimados neste momento?
7. Se voce tivesse que cortar 50% do escopo da fase para chegar mais rapido ao piloto, o que cortaria?

## Material principal para ler

Comecar por estes arquivos:

1. [README.md](/Users/tharsovieira/Documents/DailyLife/Prumo/README.md)
2. [CHANGELOG.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CHANGELOG.md)
3. [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md)
4. [HOST-ADAPTER-IMPLEMENTATION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/HOST-ADAPTER-IMPLEMENTATION-PLAN.md)
5. [PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md](/Users/tharsovieira/Documents/DailyLife/Prumo/PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md)
6. [runtime/prumo_runtime/daily_operator.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/daily_operator.py)
7. [runtime/prumo_runtime/commands/start.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/commands/start.py)
8. [runtime/prumo_runtime/commands/briefing.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/commands/briefing.py)

## Como responder

Responder em 4 blocos:

1. `Veredito`
   Diga em 3 a 6 linhas o que o Prumo e hoje e qual o risco principal.

2. `O que esta forte`
   Liste so o que parece realmente bom e defensavel.

3. `O que esta torto`
   Liste bugs conceituais, riscos, premissas frageis e pontos cegos.

4. `Proximo corte`
   Diga o que voce implementaria nas proximas 1 a 2 semanas e o que voce explicitamente nao faria agora.

## Regra de ouro para o reviewer

Nao responda como consultor de innovation theater.
Responda como alguem que vai ser responsabilizado se este piloto passar vergonha.
