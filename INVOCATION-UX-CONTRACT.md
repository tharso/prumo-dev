# Contrato de Invocação do Prumo

> Fonte canônica atual: [canon/contracts/invocation.md](/Users/tharsovieira/Documents/DailyLife/Prumo/canon/contracts/invocation.md)
>
> Este arquivo continua útil como explicação de produto e contexto de migração. A regra viva, porém, já não deveria morar só aqui.

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
prumo briefing --workspace /caminho/do/workspace --refresh-snapshot --format json
```

O `start` já tenta inferir o workspace pelo diretório atual ou por um pai reconhecível. E o binário `prumo`, sem subcomando, já deve cair nesse mesmo fluxo. Se nem isso acontecer, a campainha ainda está parafusada pelo lado de dentro.

## UX final desejada

O contrato de produto é:

1. `Cowork`: `/prumo` ou affordance equivalente;
2. `Claude Code`: affordance curta ou mensagem natural que faça o host rodar `prumo start`;
3. `Codex`: comando curto, skill ou mensagem natural que faça o host rodar `prumo start`;
4. `Gemini CLI`: idem;
5. `Antigravity` e afins: idem;
6. hosts sem shell local: não fingir suporte. Se não conseguem bater na porta, que assumam a limitação em vez de vender telepatia.

Observação de governança:

1. este contrato vale por host, não por família de modelo;
2. `Cowork` e `Claude Code` não devem ser tratados como o mesmo adapter;
3. `Gemini CLI` e `Antigravity` também não.

## Contrato do adapter

Um adapter fino deve:

1. resolver o workspace ativo;
2. chamar `prumo start` como primeiro ponto de contato;
3. devolver a resposta do runtime sem reescrever o produto em cima dela;
4. chamar `prumo briefing` diretamente apenas quando a intenção do usuário for briefing explícito;
5. se precisar de briefing estruturado, usar `prumo briefing --workspace . --refresh-snapshot --format json`;
6. usar `prumo start --format json` quando o host quiser uma porta estruturada de entrada.
7. quando depender de arquivos-guia do workspace (`AGENTS.md`, `CLAUDE.md`), manter esses wrappers alinhados com a mesma porta curta em vez de deixá-los agir como bilhete passivo.
8. ao consumir `prumo start --format json`, obedecer ao campo `kind`:
   - `shell`: executar `shell_command`;
   - `host-prompt`: usar `host_prompt` como próxima ação/fala do host.
9. ao consumir `prumo start --format json`, usar também:
   - `adapter_contract_version` para detectar mudança de contrato;
   - `workspace_resolution` para saber se o runtime inferiu o workspace ou recebeu caminho explícito;
   - `adapter_hints.preferred_entrypoint`, `briefing_entrypoint`, `briefing_structured_entrypoint` e `structured_entrypoint` para parar de adivinhar qual porta usar em cada intenção.

Um adapter fino não deve:

1. reinventar setup;
2. reinventar migrate;
3. inventar heurística paralela para repair/auth;
4. chamar o briefing como porta universal se o runtime já sabe oferecer opções melhores;
5. vender uma affordance curta que na prática cai em fluxo legado desconectado do runtime.
6. interpretar prosa como se fosse comando só porque o JSON tinha cara de estrutura.

## Como cada host deve se comportar

### Cowork

1. `/prumo` deve tentar bridge para `start`;
2. `/prumo:briefing` ou `/briefing` podem continuar tentando `briefing` por compatibilidade;
3. se o bridge falhar com `12`, cair para o legado sem espetáculo;
4. se falhar com outro código, avisar em uma linha curta e cair para o legado.
5. o host não deve ler arquivo, puxar integração por fora nem escrever `_state/` só porque a rota curta falhou.
6. se `Prumo` ou `/prumo` não conseguirem bater em `prumo`, isso é falha do adapter. Não é licença para montar um Prumo paralelo com fita crepe.

### Claude Code

1. se o usuário disser "Prumo", "bom dia, Prumo" ou equivalente, o adapter deve rodar `prumo start`;
2. se o usuário pedir briefing explicitamente, pode rodar `prumo briefing --refresh-snapshot`;
3. não deve depender de slash command, plugin store ou bridge legado do Cowork para bater na porta do runtime.

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

Observação de campo:

1. hoje, `Cowork` já provou valor como `shell-thin host`;
2. hoje, `Cowork` ainda não provou valor como invocação curta/nativa confiável.
