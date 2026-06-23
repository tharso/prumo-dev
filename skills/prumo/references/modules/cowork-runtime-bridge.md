# Cowork Runtime Bridge

> **module_version: 4.18.0**
>
> Fonte canônica do bridge experimental entre Cowork e o runtime local do Prumo.

## Objetivo

Quando o workspace já estiver no trilho novo (`AGENT.md` + `.prumo/state/workspace-schema.json`) e houver shell, o Cowork deve preferir delegar o comando ao runtime local em vez de reexecutar a lógica inteira dentro do host.

Isso não é culto ao subprocesso. É parar de fingir que o plugin ainda precisa ser o motor.

## Script canônico

- `prumo_cowork_bridge.py`

Resolver o script pela política de `runtime-paths.md`.

## Comandos suportados nesta fase

1. `start`
2. `briefing`
3. `context-dump`
4. `repair`
5. `setup`

## Regra operacional da invocação curta

Se o host oferecer uma porta curta do tipo `/prumo`, `@Prumo`, `bom dia, Prumo` ou affordance equivalente, o adapter fino deve tentar o runtime com `start` antes de qualquer outra coisa.

Fluxo:

1. resolver o workspace ativo;
2. tentar rodar:

```bash
python3 <script-resolvido> --workspace <workspace> --command start
```

3. Se o bridge sair com código `0`, devolver a saída do runtime e encerrar.
4. Se o bridge sair com código `12`, cair para o fluxo legado do host.
5. Se o bridge falhar com outro código, avisar em uma linha curta e cair para o fluxo legado.

Isso vale inclusive para workspace legado. O `start` existe justamente para orientar setup, migrate ou briefing sem exigir que o host adivinhe qual subcomando merece abrir a manhã.

## Regra operacional do `/briefing`

O briefing é a **curadoria rica** (`briefing-procedure.md`) — email/agenda + panorama numerado único → `decidir`. O cartão do runtime é a **prévia**, não o briefing. Por isso o bridge **não finaliza `/briefing` na saída do runtime**.

1. Conduzir o briefing rico do fluxo da skill: curar email/agenda via MCP quando disponível, entregar panorama numerado único e oferecer `decidir` se houver 6+ itens. **Sem MCP**, entregar o panorama local e declarar email/agenda indisponíveis em uma linha.
2. `python3 <script-resolvido> --workspace <workspace> --command briefing --format json` pode ser lido como **painel local/semente** da parte determinística — mas **nunca** é a resposta final do briefing.
3. Ao final, registrar o dia: `prumo briefing --workspace <workspace> --mark-done`.
4. Workspace legado ou sem shell: fluxo manual da skill, não o bridge.

A regra "rodar o runtime, devolver a saída e encerrar" continua valendo para a **prévia** (`/prumo`, invocação curta → `start`), nunca para o briefing.

## Guardrails

1. Na **prévia** (`start`), não paraphrasear a saída do runtime se o bridge funcionou: devolver e encerrar. No **briefing**, o oposto — o runtime é semente, a curadoria rica é a resposta.
2. Não tratar ausência de bridge como bug fatal.
3. Não bloquear o briefing por causa do experimento.
4. Não reimplementar a lógica do runtime dentro do script do bridge.

## Saída esperada

O usuário deve sentir duas coisas:

1. quando o trilho novo está ativo, o Cowork só faz o papel de interface;
2. quando não está, o produto continua funcionando pelo caminho antigo sem espetáculo.
