# Cowork Runtime Bridge

> **module_version: 4.9.2**
>
> Fonte canônica do bridge experimental entre Cowork e o runtime local do Prumo.

## Objetivo

Quando o workspace já estiver no trilho novo (`AGENT.md` + `_state/workspace-schema.json`) e houver shell, o Cowork deve preferir delegar o comando ao runtime local em vez de reexecutar a lógica inteira dentro do host.

Isso não é culto ao subprocesso. É parar de fingir que o plugin ainda precisa ser o motor.

## Script canônico

- `prumo_cowork_bridge.py`

Resolver o script pela política de `runtime-paths.md`.

## Comandos suportados nesta fase

1. `briefing`
2. `context-dump`
3. `repair`
4. `setup`

## Regra operacional do `/briefing`

Antes de carregar o procedimento legado:

1. verificar se existe `AGENT.md` no workspace;
2. verificar se existe `_state/workspace-schema.json`;
3. verificar se há shell;
4. tentar rodar:

```bash
python3 <script-resolvido> --workspace <workspace> --command briefing
```

5. Se o bridge sair com código `0`, devolver a saída como resposta final e encerrar.
6. Se o bridge sair com código `12` (`bridge-disabled`), seguir silenciosamente para o fluxo legado.
7. Se o bridge sair com código `13` ou outro erro, avisar em uma linha curta que o runtime experimental falhou e seguir para o fluxo legado.

## Guardrails

1. Não paraphrasear a saída do runtime se o bridge funcionou. Devolver e encerrar.
2. Não tratar ausência de bridge como bug fatal.
3. Não bloquear o briefing por causa do experimento.
4. Não reimplementar a lógica do runtime dentro do script do bridge.

## Saída esperada

O usuário deve sentir duas coisas:

1. quando o trilho novo está ativo, o Cowork só faz o papel de interface;
2. quando não está, o produto continua funcionando pelo caminho antigo sem espetáculo.
