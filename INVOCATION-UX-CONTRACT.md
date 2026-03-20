# Contrato de Invocação do Prumo

Este documento existe para impedir que o produto volte a escorregar para o erro clássico: um runtime bom com cinco portas tortas, uma por host, e nenhuma que o usuário consiga achar sem mapa.

## Regra-mãe

O usuário não deveria precisar pensar em subcomando.

Depois de instalar o Prumo e fazer setup/migrate uma vez, a experiência-alvo é:

1. abrir o host;
2. chamar o Prumo por uma porta curta;
3. receber orientação do runtime (`briefing`, `continuar`, `repair`, `auth`, `setup`, `migrate`) sem o host improvisar produto.

Em português simples: host não é cérebro. Host é campainha.

## Porta técnica atual

Hoje, a porta técnica canônica é:

```bash
prumo
prumo start
```

Quando necessário:

```bash
prumo start --workspace /caminho/do/workspace
prumo start --format json
```

O `start` já tenta inferir o workspace pelo diretório atual ou por um pai reconhecível. E o binário `prumo`, sem subcomando, já deve cair nesse mesmo fluxo. Se nem isso acontecer, a campainha ainda está parafusada pelo lado de dentro.

## UX final desejada

O contrato de produto é:

1. `Cowork` ou `Claude/Cowork`: `/prumo` ou affordance equivalente;
2. `Codex`: comando curto, skill ou mensagem natural que faça o host rodar `prumo start`;
3. `Gemini CLI`: idem;
4. `Antigravity` e afins: idem;
5. hosts sem shell local: não fingir suporte. Se não conseguem bater na porta, que assumam a limitação em vez de vender telepatia.

## Contrato do adapter

Um adapter fino deve:

1. resolver o workspace ativo;
2. chamar `prumo start` como primeiro ponto de contato;
3. devolver a resposta do runtime sem reescrever o produto em cima dela;
4. chamar `prumo briefing` diretamente apenas quando a intenção do usuário for briefing explícito;
5. usar `prumo start --format json` quando o host conseguir renderizar ações/interações próprias.
6. quando depender de arquivos-guia do workspace (`AGENTS.md`, `CLAUDE.md`), manter esses wrappers alinhados com a mesma porta curta em vez de deixá-los agir como bilhete passivo.

Um adapter fino não deve:

1. reinventar setup;
2. reinventar migrate;
3. inventar heurística paralela para repair/auth;
4. chamar o briefing como porta universal se o runtime já sabe oferecer opções melhores;
5. vender uma affordance curta que na prática cai em fluxo legado desconectado do runtime.

## Como cada host deve se comportar

### Cowork

1. `/prumo` deve tentar bridge para `start`;
2. `/prumo:briefing` ou `/briefing` podem continuar tentando `briefing` por compatibilidade;
3. se o bridge falhar com `12`, cair para o legado sem espetáculo;
4. se falhar com outro código, avisar em uma linha curta e cair para o legado.

### Codex

1. se o usuário disser "Prumo", "bom dia, Prumo" ou equivalente, o adapter/skill deve rodar `prumo start`;
2. se o usuário pedir briefing explicitamente, pode rodar `prumo briefing --refresh-snapshot`;
3. se o host tiver acesso a shell e arquivos locais, não há desculpa para fingir que o runtime não existe.

### Gemini CLI

Mesma lógica do Codex. A diferença aqui não é produto. É só personalidade da interface.

## Critério de sucesso

Diremos que a invocação está no trilho certo quando:

1. o usuário puder chamar o Prumo de forma curta;
2. o host encaminhar isso para `prumo start`;
3. o runtime devolver a condução certa sem o host precisar brincar de gerente de aeroporto.

Se o usuário ainda precisar decorar `prumo briefing --workspace ...` para ter valor, o motor pode até estar bom. A ignição ainda não está.
