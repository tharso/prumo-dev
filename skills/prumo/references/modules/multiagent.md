# Multiagent

> **module_version: 4.17.0**
>
> Fonte canônica da convivência entre agentes no Prumo.

## Princípios

1. Cooperação explícita, não competição.
2. Um agente altera estado por vez em cada escopo crítico.
3. Mudança estrutural relevante pede validação cruzada rastreável.

## Arquivos de estado

1. `.prumo/state/agent-lock.json`
2. `.prumo/state/HANDOVER.md`
3. `.prumo/state/HANDOVER.summary.md`

## Lock

Campos mínimos:

- `owner`
- `scope`
- `started_at`
- `ttl_minutes`

Regras:

1. sem lock ativo no escopo, o agente pode operar;
2. com lock ativo de outro agente, não escrever;
3. lock expirado pode ser assumido, registrando o motivo no handover.

## Handover

Abrir handover quando houver:

1. mudança no `.prumo/system/PRUMO-CORE.md`;
2. mudança em setup, comandos, inbox, auditoria ou integrações;
3. correção de bug sistêmico;
4. refatoração que altere comportamento de briefing ou revisão.

## Checagem no briefing

Durante `/prumo:briefing`:

1. preferir `.prumo/state/HANDOVER.summary.md`;
2. fallback para `.prumo/state/HANDOVER.md`;
3. destacar itens `PENDING_VALIDATION` e `REJECTED`;
4. se o handover estiver endereçado ao agente atual, propor ação explícita.

## Comando `/prumo:handover`

Operações esperadas:

1. `abrir`
2. `responder`
3. `fechar`
4. `listar pendentes`

## Formato mínimo

1. `ID`, `Data`, `De`, `Para`, `Status`
2. resumo da mudança
3. arquivos tocados
4. checklist objetivo de validação
5. resultado: `APPROVED` ou `REJECTED`

## Fechamento

Fluxo recomendado:

`PENDING_VALIDATION -> APPROVED/REJECTED -> CLOSED`
