---
name: higiene
description: >
  Higiene assistida do CLAUDE.md. Diagnostica duplicações, redundâncias e
  conflitos, classifica drift de conteúdo por arquivo, gera relatório e patch
  proposto, e só aplica com confirmação explícita do usuário. Use com /higiene.
---

# Higiene Assistida do Prumo

Você está executando o comando `/higiene`.

Isto não é sanitização operacional. É revisão assistida do `CLAUDE.md`.
Também é checagem de governança do que pertence a cada arquivo vivo do Prumo.

## Carregamento obrigatório

1. Leia `CLAUDE.md`.
2. Leia `PRUMO-CORE.md`.
3. Leia:
   - `Prumo/cowork-plugin/skills/prumo/references/modules/claude-hygiene.md`
   - `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-file-governance.md`
4. Quando houver shell, carregue também:
   - `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-paths.md`

## Fluxo

1. Rodar diagnóstico do `CLAUDE.md`.
2. Mostrar o resultado em 3 blocos fixos, nesta ordem:
   - `Mudanças seguras`
   - `Itens que pedem confirmação factual`
   - `Decisões de governança/arquitetura`
   `Mudanças seguras` só pode conter o que o patch atual consegue aplicar sem interpretação.
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
- Nunca mover item entre arquivos sem confirmação factual do usuário.
- Nunca misturar no mesmo bloco limpeza segura, confirmação factual e decisão de governança.
- Se o `PRUMO-CORE.md` do workspace estiver defasado em relação ao runtime, sinalizar isso explicitamente.
- Se o conflito for interpretativo demais, reportar e deixar a decisão para o usuário.
