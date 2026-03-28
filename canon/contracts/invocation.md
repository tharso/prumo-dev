# Contrato de Invocacao

Data de extracao: 2026-03-28

Este arquivo e a fonte canonica da invocacao do Prumo como produto. Implementacao de runtime, wrapper e adapter devem obedecer a este contrato, nao inventar outro no estacionamento.

## Regra-mae

O usuario nao deveria precisar pensar em subcomando.

Depois de instalar o Prumo e fazer `setup` ou `migrate`, a experiencia alvo e:

1. abrir o host;
2. chamar o Prumo por uma porta curta;
3. receber orientacao do motor sem o host improvisar um produto paralelo.

## Porta tecnica atual

Hoje, a porta tecnica canonica e:

```bash
prumo
prumo start
```

Quando necessario:

```bash
prumo start --workspace /caminho/do/workspace
prumo start --format json
prumo briefing --workspace /caminho/do/workspace --refresh-snapshot
prumo briefing --workspace /caminho/do/workspace --refresh-snapshot --format json
```

## Contrato do adapter

Um adapter fino deve:

1. resolver o workspace ativo;
2. chamar `prumo` ou `prumo start` como primeiro ponto de contato;
3. chamar `prumo briefing` diretamente apenas quando o pedido for briefing explicito;
4. usar `prumo start --format json` quando o host quiser entrada estruturada;
5. usar `prumo briefing --format json` quando o host precisar de briefing estruturado;
6. respeitar `adapter_hints` e `actions[]` retornados pelo runtime;
7. tratar `AGENT.md`, `CLAUDE.md` e `AGENTS.md` como wrappers de acesso, nao como licenca para simular o motor.

Um adapter fino nao deve:

1. reinventar `setup`, `migrate`, `repair` ou `auth`;
2. transformar `briefing` na porta universal por preguiça;
3. escrever `_state/` manualmente fingindo ser o runtime;
4. fabricar JSON de resposta;
5. usar leitura de arquivo como substituto do comando real quando ha shell disponivel.

## Comportamento por intencao

### Invocacao curta

Se o usuario disser `Prumo`, `bom dia, Prumo` ou equivalente:

1. o host deve tentar `prumo`;
2. se preferir rota estruturada, pode usar `prumo start --format json`;
3. o host nao deve responder com briefing inventado sem antes bater no runtime.

### Briefing explicito

Se o usuario pedir briefing:

1. o host pode rodar `prumo briefing --workspace . --refresh-snapshot`;
2. se precisar de estrutura, pode usar `--format json`;
3. se o briefing falhar, o host deve informar a falha de forma clara e curta, nao compensar com teatro.

### Execucao de proximo movimento

Se `prumo start --format json` recomendar uma acao e o usuario responder `1`, `a`, `aceitar`, `seguir` ou equivalente:

1. o host deve executar o proximo movimento recomendado;
2. nao deve rerodar `start` so para se sentir acompanhado;
3. deve reportar resultado e mudancas documentais antes de oferecer novo menu.

## Fronteira entre contrato e implementacao

Este arquivo define:

1. qual e a porta;
2. quando usar cada porta;
3. o que o host pode e nao pode improvisar.

Este arquivo nao define:

1. shell path especifico;
2. fallback de Cowork;
3. bridge historico de plugin;
4. detalhes de interface grafica de cada host.

Isso mora em runtime e adapters.
