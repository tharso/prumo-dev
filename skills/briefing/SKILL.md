---
name: briefing
description: >
  Morning briefing do Prumo. Executa a rotina completa: lê configuração pessoal,
  verifica pauta, processa inbox (todos os canais), checa calendário e emails,
  e apresenta o briefing do dia. Use com /prumo:briefing (alias legado: /briefing) ou quando o usuário disser
  "bom dia", "briefing", "começar o dia".
---

# Briefing do Prumo

Você está rodando o morning briefing do Prumo.

O procedimento completo está nos módulos. Aqui só tem o mapa de onde cada coisa mora e as regras que não podem ser puladas.

## Carregamento obrigatório

1. Leia `Prumo/Agente/PERFIL.md`.
2. Leia `.prumo/system/PRUMO-CORE.md`.
3. Leia o módulo canônico:
   - `skills/prumo/references/modules/briefing-procedure.md`
4. Quando disponíveis, carregue também:
   - `skills/prumo/references/modules/load-policy.md`
   - `skills/prumo/references/modules/version-update.md`
   - `skills/prumo/references/modules/interaction-format.md`
   - `skills/prumo/references/modules/runtime-paths.md`
   - `skills/prumo/references/modules/cowork-runtime-bridge.md`

Se o repo `Prumo/` não estiver acessível, use o bundle instalado. O que não vale é inventar atalho e chamar de interpretação.

## Tentar o runtime novo primeiro

Se tiver shell e o workspace estiver no formato novo (`AGENT.md` + `.prumo/state/workspace-schema.json`):

1. Tentar rodar o briefing pelo runtime.
2. Se funcionar, entregar a resposta e pronto.
3. Se não funcionar, seguir pro fluxo normal sem drama.

A resposta do runtime vai como veio. Não reescrever, não enfeitar.

## Quando o briefing roda

1. Se o usuário disser "bom dia" ou invocar o Prumo de forma curta, tentar `start` primeiro.
2. Se pedir briefing explicitamente, ir direto pro briefing.
3. Não inventar onboarding ou repair por conta própria — o runtime sabe fazer isso.

## Quem manda em caso de conflito

1. `ASSERT:` do `.prumo/system/PRUMO-CORE.md`
2. O módulo do briefing
3. Este arquivo

## Módulos operacionais do briefing

- briefing detalhado:
  - `skills/prumo/references/modules/briefing-procedure.md`
- inbox e preview:
  - `skills/prumo/references/modules/inbox-processing.md`
- update seguro:
  - `skills/prumo/references/modules/version-update.md`
- multiagente:
  - `skills/prumo/references/modules/multiagent.md`
- runtime paths:
  - `skills/prumo/references/modules/runtime-paths.md`
- contrato de interface:
  - `skills/prumo/references/modules/interaction-format.md`

## Regras que não podem ser puladas

- Usar Gmail MCP e Calendar MCP como fonte primária de email e calendário.
- Se existir `_preview-index.json`, linkar `inbox-preview.html` antes de abrir bruto.
- Persistir `last_briefing_at` antes da primeira resposta.
- `interrupted_at` e `resume_point` só existem se o usuário pediu pra parar.
- Update que não consegue se aplicar sozinho não trava o briefing.
- Se houver versão nova detectável, o briefing deve avisar antes do panorama e oferecer alternativas curtas.
- Se o `.prumo/system/PRUMO-CORE.md` do workspace estiver atrás do `Prumo/VERSION` local, isso deve ser tratado como core defasado do workspace, não como detalhe invisível.
- Se tiver shell e o workspace estiver no formato novo, tentar o runtime antes.
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
- email e calendário via Gmail/Calendar MCP direto;
- curadoria em `Responder`, `Ver`, `Sem ação` com `P1/P2/P3`.

## Aviso

Se pular a leitura do módulo do briefing pra “economizar”, só repete o bug que causou essa refatoração. A economia aí é de palito de fósforo.
