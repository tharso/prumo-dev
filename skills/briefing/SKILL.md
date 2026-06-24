---
name: briefing
description: >
  Morning briefing do Prumo. Executa a rotina completa: lê configuração pessoal,
  verifica pauta, processa inbox (todos os canais), checa calendário e emails,
  e apresenta o briefing do dia. Use com /prumo:briefing (alias legado: /briefing)
  ou quando o usuário pedir explicitamente "briefing", "começar o dia",
  "painel do dia", "o que tem pra hoje". Não dispara em saudação curta como
  "prumo" cru ou "ei prumo" — para invocação curta sem intenção explícita,
  use `prumo:abrir`.
---

# Briefing do Prumo

Você está rodando o morning briefing do Prumo.

O procedimento completo está nos módulos. Aqui só tem o mapa de onde cada coisa mora e as regras que não podem ser puladas.

## Carregamento obrigatório

1. Leia `Prumo/Agente/PERFIL.md`.
2. Leia `.prumo/system/PRUMO-CORE.md`.
3. Leia o módulo canônico:
   - `skills/prumo/references/modules/briefing-procedure.md`
4. Se `Inbox4Mobile/` existir no workspace, leia também:
   - `skills/prumo/references/modules/inbox-processing.md`
5. Quando disponíveis, carregue também:
   - `skills/prumo/references/modules/load-policy.md`
   - `skills/prumo/references/modules/version-update.md`
   - `skills/prumo/references/modules/interaction-format.md`
   - `skills/prumo/references/modules/runtime-paths.md`
   - `skills/prumo/references/modules/cowork-runtime-bridge.md`

Se o repo `Prumo/` não estiver acessível, use o bundle instalado. O que não vale é inventar atalho e chamar de interpretação.

## O runtime é a prévia, não o briefing

O cartão do runtime (`prumo start` / `prumo briefing`) é a **prévia** — retrato rápido e local (pauta, inbox, próximo movimento). O **briefing** é a curadoria rica deste fluxo: email/agenda + panorama numerado único → `decidir`.

1. Pedir "briefing" dispara a **curadoria rica** (`briefing-procedure.md`). **Nunca** entregar o cartão do runtime como briefing final — entregar a prévia e parar é o beco sem saída que esta refatoração corrige.
2. `prumo briefing --workspace <path> --format json` pode ser lido como **painel local** (semente da parte determinística), mas a resposta é o panorama numerado rico.
3. Ao final, registrar o dia: `prumo briefing --workspace <path> --mark-done`.
4. A regra "entregar a saída do runtime como veio e encerrar" vale para a **prévia** (`prumo start` / `prumo:abrir`), **não** para o briefing.

## Quando o briefing roda

1. Briefing roda apenas com pedido explícito ("briefing", "painel do dia", "o que tem pra hoje", "começar o dia"). Saudação curta tipo "prumo" cru ou "ei prumo" não dispara briefing — vai para `prumo:abrir`, que decide o caminho a partir do scan.
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
- Usar Gmail MCP e Calendar MCP como fonte primária de email e calendário **quando disponíveis**. Seguir o pipeline de curadoria em camadas definido em `briefing-procedure.md` (camada 1: canais prioritários, camada 2: emails diretos com filtragem pessoa/sistema, camada 3: roteamento de conteúdo). **Sem MCP**: entregar o panorama local (pauta, inbox, calendário se acessível) e declarar em uma linha que email/agenda estão indisponíveis — nunca cair de volta no cartão da prévia.
- Antes de curar emails, ler `Prumo/Referencias/EMAIL-CURADORIA.md` (se existir) para carregar regras aprendidas. Quando o usuário corrigir a curadoria, registrar a regra nesse arquivo.
- Se existir `_preview-index.json`, linkar `inbox-preview.html` antes de abrir bruto.
- Se o panorama tiver 6+ itens acionáveis, oferecer o despacho visual da skill `decidir` (HTML interativo offline) além do chat, reusando os números do panorama. Override do usuário sempre respeitado; se a geração falhar, cair no chat. Ver `briefing-procedure.md` → "Despacho visual" e `skills/decidir/SKILL.md`.
- Update que não consegue se aplicar sozinho não trava o briefing.
- Se houver versão nova detectável, o briefing deve avisar antes do panorama e seguir. **"Detectável" inclui o `VERSION` remoto** (`raw.githubusercontent.com/tharso/prumo/main/VERSION`): no fluxo manual sem runtime, buscar via WebFetch/`curl` é o caminho — comparar só o core local **não** é a checagem. Se não der pra buscar de jeito nenhum, avisar que não checou; nunca dizer "versão em dia" sem ter comparado.
- Se o `.prumo/system/PRUMO-CORE.md` do workspace estiver atrás do `Prumo/VERSION` local, isso deve ser tratado como core defasado do workspace, não como detalhe invisível.
- Se tiver `prumo` no PATH e o workspace estiver no formato novo, o runtime pode dar a **prévia** rápida (`prumo start`) — mas o briefing é a curadoria rica, não o cartão. Não encerrar na prévia.

## Resultado esperado

O briefing entrega:

- panorama numerado único: agenda, emails curados e pendências numerados sequencialmente de 1 a N;
- proposta do dia em seguida, com opções curtas para responder;
- curadoria de email: classificação em `Responder` / `Ver` / `Sem ação` com prioridade P1 (ação hoje) / P2 (ação esta semana) / P3 (informativo);
- email e calendário via Gmail/Calendar MCP direto.

## Aviso

Se pular a leitura do módulo do briefing pra “economizar”, só repete o bug que causou essa refatoração. A economia aí é de palito de fósforo.
