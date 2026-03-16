---
name: higiene
description: >
  Higiene assistida do CLAUDE.md. Diagnostica duplicações, redundâncias e
  conflitos, gera relatório e patch proposto, e só aplica com confirmação
  explícita do usuário. Use com /prumo:higiene.
---

# Higiene Assistida do Prumo

Você está executando o comando `/prumo:higiene`.

Isto não é sanitização operacional. É revisão assistida do `CLAUDE.md`.

## Carregamento obrigatório

1. Leia `CLAUDE.md`.
2. Leia `PRUMO-CORE.md`.
3. Leia:
   - `Prumo/cowork-plugin/skills/prumo/references/modules/claude-hygiene.md`
4. Quando houver shell, carregue também:
   - `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-paths.md`

## Fluxo

1. Rodar diagnóstico do `CLAUDE.md`.
2. Mostrar duplicações, redundâncias e conflitos potenciais.
3. Apontar onde está o patch proposto.
4. Perguntar se o usuário quer aplicar.
5. Só com confirmação explícita:
   - aplicar a proposta;
   - criar backup;
   - registrar em `REGISTRO.md`.

## Guardrails

- `CLAUDE.md` nunca entra em autosanitização.
- Nunca aplicar sem confirmação explícita.
- Nunca reescrever preferências subjetivas por conta própria.
- Se o conflito for interpretativo demais, reportar e deixar a decisão para o usuário.
