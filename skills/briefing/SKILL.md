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

Você está rodando o morning briefing do Prumo. A rota é **fásica** (#180): cada material carrega **na fase que o usa**.

## Mapa de carregamento por fase

A **lista canônica ÚNICA** de carregamento do briefing (#195, emendada pela #180: a Pré-carga virou este mapa). Nenhum outro arquivo mantém segunda enumeração — duas listas, uma é drift. Gatilho `sempre` carrega na abertura da fase; os demais, **no primeiro uso real** (deferred-load ≠ deferred-run: a obrigação RODA na fase dela; o texto só abre quando tem trabalho).

| Fase | Gatilho | Arquivo | Seção | Tipo |
|---|---|---|---|---|
| F0 | sempre | `CLAUDE.md` | (integral) | wrapper da raiz |
| F0 | sempre | `Prumo/AGENT.md` | (integral) | porta canônica |
| F0 | sempre | `.prumo/system/PRUMO-CORE.md` | até: `# Parte 2 — Playbooks operacionais` | core (Parte 1) |
| F0 | sempre | `.prumo/skills/prumo/references/modules/dispatch.md` | (integral) | protocolo de abertura (#248) |
| F1 | sempre | `.prumo/skills/briefing/SKILL.md` | (integral) | esta skill |
| F1 | sempre | `.prumo/skills/prumo/references/modules/briefing-procedure.md` | (integral) | espinha |
| F1 | sempre | `.prumo/system/PRUMO-CORE.md` | `## Guardrails` | core (seção) |
| F1 | sempre | `Prumo/Agente/PERFIL.md` | (integral) | config do usuário |
| F1 | sempre | `Prumo/Agente/ROTINA.md` | (integral) | config do usuário |
| F1 | sempre | `Prumo/Agente/PESSOAS.md` | (integral) | predicado de remetente |
| F1 | sempre | `.prumo/skills/prumo/references/modules/briefing-estado.md` | (integral) | estado operacional |
| F1 | sempre | `.prumo/skills/prumo/references/modules/version-preflight.md` | (integral) | preflight de versão |
| F1 | oferta/execução de update (warning/alert) | `.prumo/skills/prumo/references/modules/version-update.md` | (integral) | canônico do update |
| F1 | scripts via shell | `.prumo/skills/prumo/references/modules/runtime-paths.md` | (integral) | resolução de scripts |
| F1 | shell com runtime alcançável | `.prumo/skills/prumo/references/modules/cowork-runtime-bridge.md` | (integral) | ponte do runtime |
| F1 | antes de invocar comando do runtime (escolha de formato inclusa) | `.prumo/skills/prumo/references/modules/runtime-consumo.md` | (integral) | contrato de consumo |
| F1 | sempre | `.prumo/skills/prumo/references/modules/faxina-thresholds.md` | (integral) | números da faxina (defaults + overrides) |
| F1 | override do usuário existir | `Prumo/Custom/rules/faxina-thresholds.md` | (integral) | thresholds customizados |
| F1 | família de faxina pendente (execução — a checagem mínima mora no estado) | `.prumo/skills/prumo/references/modules/faxina.md` | (integral) | executor da faxina |
| F2 | antes da triagem local do Inbox4Mobile OU de abrir email/agenda | `.prumo/skills/prumo/references/modules/briefing-canais.md` | (integral) | canais + defesas |
| F2 | Inbox4Mobile com itens novos | `.prumo/skills/prumo/references/modules/inbox-processing.md` | (integral) | triagem do inbox |
| F2 | antes de filtrar email (se existir) | `Prumo/Referencias/EMAIL-CURADORIA.md` | (integral) | regras aprendidas |
| F2 | canal de email disponível E EMAIL-CURADORIA.md ausente (criação) | `.prumo/skills/prumo/references/file-templates.md` | `## Prumo/Referencias/EMAIL-CURADORIA.md` | template canônico |
| F2 | aprofundamento (predicado g / fallback por fonte) | `.prumo/skills/prumo/references/modules/load-policy.md` | (integral) | política de leitura |
| F3 | ao montar o panorama | `.prumo/skills/prumo/references/modules/briefing-montagem.md` | (integral) | dois tempos + fechamento |
| F3 | ao montar o panorama | `.prumo/skills/prumo/references/modules/interaction-format.md` | (integral) | dono da numeração |
| F3 | 6+ itens acionáveis (#218) | `.prumo/skills/decidir/SKILL.md` | (integral) | despacho visual |

**F4 (fechamento)** não carrega material novo: executa a seção `## Escrita e fechamento` de `briefing-montagem.md` (já em contexto desde F3) — escrita nos canais, `_processed.json` e a marcação do dia. F4 existe como FASE do contrato (#177/#180); ausência de linha na tabela é design, não omissão.

Cada item lido **uma vez**; se já está no contexto, não reler. Repo `Prumo/` inacessível → usar o bundle instalado; atalho inventado não é interpretação.

## Carregamento obrigatório

O mapa acima é a única lista deste briefing. A **espinha** (`briefing-procedure.md`) manda na ordem dos passos; em conflito com este resumo, a espinha vence; `ASSERT:` do core vence tudo.

## O runtime é a prévia, não o briefing

Pedir "briefing" dispara a curadoria rica (espinha + fases). **Nunca** entregar o cartão do runtime (`prumo start`) como briefing final — o briefing é curadoria em **dois tempos na mesma resposta** (#196), numeração única que nunca reinicia. Variante completa marca o dia (`--mark-done` — regras na montagem).

## Quando o briefing roda

Apenas com pedido explícito ("briefing", "painel do dia", "o que tem pra hoje", "começar o dia"). Saudação curta ("prumo" cru) vai para `prumo:abrir`. Não inventar onboarding ou repair por conta própria — o runtime sabe fazer isso.

## Regras que não podem ser puladas (resumo — o dono de cada uma está no mapa)

- **Numeração sequencial única** 1..N entre seções e tempos (dono: `interaction-format.md`).
- Gmail/Calendar MCP como fonte primária **quando disponíveis**; sem MCP, panorama local + declaração em uma linha (espinha, Passo 0).
- Defesas de terceiros e pós-filtro exato (#210): **`briefing-canais.md` antes de abrir o Gmail** (F2). `EMAIL-CURADORIA.md` lido antes de filtrar; correções viram regra lá.
- Linha de faxina obrigatória no primeiro tempo (#217, montagem).
- Se o panorama tiver 6+ itens acionáveis, **gerar automaticamente o despacho visual da skill `decidir` e entregar o link pronto** — sem perguntar antes (#218); cards reusam os números; falhou, cai no chat (montagem).
- Update detectável segue o gatilho graduado do preflight (#174); nunca "em dia" sem comparar; update que não se aplica sozinho não trava o briefing.

## Resultado esperado

Panorama numerado único em dois tempos (local 1..k → emails e agenda k+1..N), proposta do dia com opções curtas, curadoria `Responder`/`Ver`/`Sem ação` com P1/P2/P3, fechamento com escrita nos canais.
