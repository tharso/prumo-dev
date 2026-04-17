# Multiagent

> **module_version: 4.19.0**
>
> Fonte canônica da convivência entre agentes no Prumo.
> Escopo: coordenação de escrita simultânea em estado compartilhado via lock.

## Princípios

1. Cooperação explícita, não competição.
2. Um agente altera estado por vez em cada escopo crítico.
3. Lock é infraestrutura: existe pra evitar corrida, não pra documentar trabalho.

## Arquivo de estado

- `.prumo/state/agent-lock.json`

## Lock

Campos mínimos:

- `owner`
- `scope`
- `started_at`
- `ttl_minutes`

Regras:

1. sem lock ativo no escopo, o agente pode operar;
2. com lock ativo de outro agente, não escrever;
3. lock expirado pode ser assumido, registrando o motivo em nota curta.

## Quando usar lock

Casos em que faz sentido segurar lock antes de escrever:

1. mudança no `.prumo/system/PRUMO-CORE.md`;
2. mudança estrutural em arquivos do `Prumo/Agente/`;
3. operação longa que toca múltiplos arquivos do workspace.

Operações rápidas e locais (atualizar PAUTA.md, registrar no REGISTRO.md) não precisam de lock.
