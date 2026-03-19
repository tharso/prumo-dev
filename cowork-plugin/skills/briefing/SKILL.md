---
name: briefing
description: >
  Morning briefing do Prumo. Executa a rotina completa: lê configuração pessoal,
  verifica pauta, processa inbox (todos os canais), checa calendário e emails,
  e apresenta o briefing do dia. Use com /prumo:briefing (alias legado: /briefing) ou quando o usuário disser
  "bom dia", "briefing", "começar o dia".
---

# Briefing do Prumo

Você está executando o morning briefing do sistema Prumo.

O fluxo detalhado não mora mais aqui. A fonte canônica agora é modular, porque o desenho antigo transformava `SKILL.md`, core e referência em versões concorrentes do mesmo ritual.

## Carregamento obrigatório

1. Leia `CLAUDE.md`.
2. Leia `PRUMO-CORE.md`.
3. Leia o módulo canônico:
   - `Prumo/cowork-plugin/skills/prumo/references/modules/briefing-procedure.md`
4. Quando disponíveis, carregue também:
   - `Prumo/cowork-plugin/skills/prumo/references/modules/load-policy.md`
   - `Prumo/cowork-plugin/skills/prumo/references/modules/version-update.md`
   - `Prumo/cowork-plugin/skills/prumo/references/modules/interaction-format.md`
   - `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-paths.md`

Se o workspace não expuser o repo `Prumo/`, use a referência equivalente do bundle instalado. O que não vale é inventar um atalho novo e chamar isso de interpretação.

## Fonte de autoridade

Em caso de conflito:

1. `ASSERT:` do `PRUMO-CORE.md`
2. módulo canônico
3. este `SKILL.md`

## Módulos operacionais do briefing

- briefing detalhado:
  - `Prumo/cowork-plugin/skills/prumo/references/modules/briefing-procedure.md`
- inbox e preview:
  - `Prumo/cowork-plugin/skills/prumo/references/modules/inbox-processing.md`
- update seguro:
  - `Prumo/cowork-plugin/skills/prumo/references/modules/version-update.md`
- multiagente:
  - `Prumo/cowork-plugin/skills/prumo/references/modules/multiagent.md`
- runtime paths:
  - `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-paths.md`
- contrato de interface:
  - `Prumo/cowork-plugin/skills/prumo/references/modules/interaction-format.md`

## Guardrails que não podem ser pulados

- Antes de Gmail MCP ou Calendar MCP, tentar snapshots no Google Drive.
- Se existir `_preview-index.json`, linkar `inbox-preview.html` antes de abrir bruto.
- Persistir `last_briefing_at` antes da primeira resposta.
- `interrupted_at` e `resume_point` só existem se o usuário acionou escape hatch.
- Update sem transporte seguro de aplicação não bloqueia briefing.
- Se houver versão nova detectável, o briefing deve avisar antes do panorama e oferecer alternativas curtas.
- Quando isso acontecer, preferir:
  - `a) atualizar agora`
  - `b) seguir mesmo assim`
  - `c) ver diagnóstico`

## Resultado esperado

O briefing continua entregando:

- `Bloco 1` de panorama;
- `Bloco 2` de proposta do dia;
- contexto completo apenas em `c` ou `/prumo:briefing --detalhe`;
- curadoria de email em `Responder`, `Ver`, `Sem ação`;
- prioridade `P1/P2/P3`;
- snapshots do Google Drive como fonte primária quando houver Google Docs `Prumo/snapshots/email-snapshot`;
- fallback com shell via script dual quando necessário;
- fallback sem shell com a mesma taxonomia.

## Observação

Se o runtime “economizar leitura” e pular o módulo canônico, ele só repete o bug que motivou essa refatoração. A economia aí é de palito de fósforo.
