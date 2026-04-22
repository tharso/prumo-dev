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

- **Numeração sequencial obrigatória**: todo item acionável (email, evento, pendência, item de inbox) recebe número sequencial único do 1 ao N, sem reiniciar entre seções. Se o panorama tem 5 emails (1-5), a agenda continua do 6. Isso permite ao usuário despachar vários itens de uma vez ("3, 7, 12").
- Usar Gmail MCP e Calendar MCP como fonte primária de email e calendário. Seguir o pipeline de curadoria em camadas definido em `briefing-procedure.md` (camada 1: canais prioritários, camada 2: emails diretos com filtragem pessoa/sistema, camada 3: roteamento de conteúdo).
- Antes de curar emails, ler `Prumo/Referencias/EMAIL-CURADORIA.md` (se existir) para carregar regras aprendidas. Quando o usuário corrigir a curadoria, registrar a regra nesse arquivo.
- Se existir `_preview-index.json`, linkar `inbox-preview.html` antes de abrir bruto.
- Update que não consegue se aplicar sozinho não trava o briefing.
- Se houver versão nova detectável, o briefing deve avisar antes do panorama e seguir.
- Se o `.prumo/system/PRUMO-CORE.md` do workspace estiver atrás do `Prumo/VERSION` local, isso deve ser tratado como core defasado do workspace, não como detalhe invisível.
- Se tiver `prumo` no PATH e o workspace estiver no formato novo, tentar o runtime antes.

## Resultado esperado

O briefing entrega:

- panorama numerado único: agenda, emails curados e pendências numerados sequencialmente de 1 a N;
- proposta do dia em seguida, com opções curtas para responder;
- curadoria de email: classificação em `Responder` / `Ver` / `Sem ação` com prioridade P1 (ação hoje) / P2 (ação esta semana) / P3 (informativo);
- email e calendário via Gmail/Calendar MCP direto.

## Aviso

Se pular a leitura do módulo do briefing pra “economizar”, só repete o bug que causou essa refatoração. A economia aí é de palito de fósforo.
