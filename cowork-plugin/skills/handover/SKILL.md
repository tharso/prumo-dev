---
name: handover
description: >
  Comando manual de handover multiagente. Use com /prumo:handover para abrir,
  responder, listar pendentes e fechar handovers fora da rotina de briefing.
---

# Handover do Prumo

Você está executando o comando `/prumo:handover`.

Objetivo: operar `_state/HANDOVER.md` de forma rastreável, cooperativa e sem fricção.

Ao responder no chat:

1. manter numeração contínua dentro do mesmo handover;
2. quando houver escolha do usuário, preferir alternativas curtas em `a)`, `b)`, `c)`;
3. não reiniciar a contagem a cada bloco como se o handover tivesse perdido a memória.

## Passo 1: Ler estado

1. Leia `_state/HANDOVER.md` (se existir).
2. Leia `_state/agent-lock.json` (se existir).

Se `_state/HANDOVER.md` não existir, crie com template mínimo de status e seções.

## Passo 2: Identificar modo

Detecte a intenção do usuário e siga um destes modos:

1. `listar`: mostrar handovers `PENDING_VALIDATION` e `REJECTED`.
2. `abrir`: criar novo handover com status `PENDING_VALIDATION`.
3. `responder`: registrar validação do agente destino (`APPROVED` ou `REJECTED`).
4. `fechar`: mover item para `CLOSED` após validação e ajustes.

Se a intenção estiver ambígua, perguntar assim:

- `a) listar`
- `b) abrir`
- `c) responder`
- `d) fechar`

## Passo 3: Operar handover

### Modo `abrir`

Adicionar item com:

1. `ID` no formato `HO-YYYY-MM-DD-XXX`
2. `Data`, `De`, `Para`, `Status`
3. Resumo
4. Arquivos alterados
5. Checklist objetivo
6. Seção de resposta do agente destino

### Modo `responder`

No ID informado, preencher:

1. `Resultado` (`APPROVED` ou `REJECTED`)
2. `Comentários`
3. `Ajustes solicitados` (se houver)
4. `Data`
5. Atualizar status no cabeçalho do item

### Modo `fechar`

No ID informado:

1. Confirmar que já existe validação (`APPROVED` ou `REJECTED` + resolução)
2. Atualizar status para `CLOSED`

## Passo 4: Tom e cooperação

Em qualquer modo:

1. Linguagem respeitosa entre agentes
2. Foco em colaboração e resolução
3. Nada de competição ou atribuição de culpa

## Passo 5: Documentar

Se a operação de handover representou mudança de estado do sistema, registrar linha em `REGISTRO.md`.
