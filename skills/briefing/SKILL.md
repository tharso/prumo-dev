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

Você está rodando o morning briefing do Prumo. Rota **fásica** (#180): cada material carrega **na fase que o usa**.

## Mapa de carregamento por fase

A **lista canônica ÚNICA** de carregamento do briefing (#195, emendada pela #180: a Pré-carga virou este mapa). Nenhum outro arquivo mantém segunda enumeração — duas listas, uma é drift. Gatilho `sempre` carrega na abertura da fase; os demais, **no primeiro uso real** (deferred-load ≠ deferred-run: a obrigação RODA na fase dela; o texto só abre quando tem trabalho).

| Fase | Gatilho | Arquivo | Seção | Tipo |
|---|---|---|---|---|
| F0 | sempre | `CLAUDE.md` | (integral) | wrapper da raiz |
| F0 | sempre | `Prumo/AGENT.md` | (integral) | porta canônica |
| F0 | sempre | `.prumo/system/PRUMO-CORE.md` | até: `# Parte 2 — Playbooks operacionais` | core P1 |
| F0 | sempre | `.prumo/skills/prumo/references/modules/dispatch.md` | até: `## Roteamento por intenção` | abertura (#248) |
| F1 | ao resolver a intenção do usuário (nunca na abertura) | `.prumo/skills/prumo/references/modules/dispatch.md` | `## Roteamento por intenção` | roteamento (#228) |
| F0 | sempre (autoral) | `Prumo/Agente/MAPA-AUTORAL.md` | (integral) | caminhos autorais (#241) |
| F1 | sempre | `.prumo/skills/briefing/SKILL.md` | (integral) | esta skill |
| F1 | sempre | `.prumo/skills/prumo/references/modules/briefing-procedure.md` | (integral) | espinha |
| F1 | sempre | `.prumo/system/PRUMO-CORE.md` | `## Guardrails` | core (seção) |
| F1 | sempre | `Prumo/Agente/PERFIL.md` | (integral) | config |
| F1 | sempre | `Prumo/Agente/ROTINA.md` | (integral) | config |
| F1 | sempre | `Prumo/Agente/PESSOAS.md` | (integral) | remetentes |
| F1 | sempre | `.prumo/skills/prumo/references/modules/briefing-estado.md` | (integral) | estado |
| F1 | sempre | `.prumo/skills/prumo/references/modules/version-preflight.md` | (integral) | preflight |
| F1 | oferta/execução de update (warning/alert) | `.prumo/skills/prumo/references/modules/version-update.md` | (integral) | canônico do update |
| F1 | scripts via shell | `.prumo/skills/prumo/references/modules/runtime-paths.md` | (integral) | scripts |
| F1 | shell com runtime alcançável | `.prumo/skills/prumo/references/modules/cowork-runtime-bridge.md` | (integral) | ponte do runtime |
| F1 | antes de QUALQUER comando do runtime (formato e invocação) | `.prumo/skills/prumo/references/modules/runtime-consumo.md` | (integral) | consumo |
| F1 | sem semente, `faxina.schema` ≠ `prumo_faxina_thresholds.v1` OU override divergente | `.prumo/skills/prumo/references/modules/faxina-thresholds.md` | (integral) | números da faxina (#258) |
| F1 | override do usuário existir | `Prumo/Custom/rules/faxina-thresholds.md` | (integral) | overrides |
| F1 | família de faxina pendente (execução — a checagem mínima mora no estado) | `.prumo/skills/prumo/references/modules/faxina.md` | (integral) | executor |
| F2 | `MAPA-AUTORAL.md` com nota (gramática dos marcadores) | `.prumo/skills/prumo/references/modules/load-policy.md` | `## Listagem de diretórios (perímetro de leitura, #194)` | marcadores (#245) |
| F2 | antes da triagem local do Inbox4Mobile, de caixa declarada OU de abrir email/agenda | `.prumo/skills/prumo/references/modules/briefing-canais.md` | (integral) | canais |
| F2 | Inbox4Mobile com itens novos | `.prumo/skills/prumo/references/modules/inbox-processing.md` | (integral) | inbox |
| F2 | antes de filtrar email (se existir) | `Prumo/Referencias/EMAIL-CURADORIA.md` | (integral) | curadoria |
| F2 | canal de email disponível E EMAIL-CURADORIA.md ausente (criação) | `.prumo/skills/prumo/references/file-templates.md` | `## Prumo/Referencias/EMAIL-CURADORIA.md` | template |
| F2 | aprofundamento (predicado g / fallback por fonte) | `.prumo/skills/prumo/references/modules/load-policy.md` | (integral) | leitura |
| F3 | ao montar o panorama | `.prumo/skills/prumo/references/modules/briefing-montagem.md` | (integral) | dois tempos |
| F3 | ao montar o panorama | `.prumo/skills/prumo/references/modules/interaction-format.md` | (integral) | numeração |
| F3 | 6+ itens acionáveis (#218) | `.prumo/skills/decidir/SKILL.md` | (integral) | despacho |

**F4 (fechamento)** não carrega material novo: executa `## Escrita e fechamento` de `briefing-montagem.md` (em contexto desde F3) — escrita nos canais, `_processed.json` e marcação do dia. É FASE do contrato (#177/#180); sem linha na tabela por design.

Cada item lido **uma vez**; já em contexto, não reler. Repo `Prumo/` inacessível → bundle instalado; atalho inventado não é interpretação.

## Carregamento obrigatório

O mapa acima é a única lista deste briefing. A **espinha** (`briefing-procedure.md`) manda na ordem dos passos; em conflito com este resumo, ela vence; `ASSERT:` do core vence tudo.

## O runtime é a prévia, não o briefing

Pedir "briefing" dispara a curadoria rica (espinha + fases). **Nunca** entregar o cartão do runtime (`prumo start`) como briefing final — o briefing é curadoria em **dois tempos na mesma resposta** (#196), numeração única que nunca reinicia. Variante completa marca o dia (`--mark-done`, montagem).

## Quando o briefing roda

Só com pedido explícito ("briefing", "painel do dia", "o que tem pra hoje", "começar o dia"). Saudação curta ("prumo" cru) vai pra `prumo:abrir`. Não inventar onboarding nem repair — o runtime sabe fazer isso.

## Regras que não podem ser puladas (resumo — o dono de cada uma está no mapa)

- **Numeração sequencial única** 1..N entre seções e tempos (dono: `interaction-format.md`).
- Gmail/Calendar MCP como fonte primária **quando disponíveis**; sem MCP, panorama local + declaração em uma linha (espinha, Passo 0).
- Defesas de terceiros e pós-filtro exato (#210): **`briefing-canais.md` antes do Gmail** (F2). `EMAIL-CURADORIA.md` antes de filtrar; correções viram regra lá.
- Linha de faxina obrigatória no primeiro tempo (#217, montagem).
- 6+ itens acionáveis: **gerar automaticamente o despacho visual da skill `decidir` e entregar o link pronto** — sem perguntar antes (#218); cards reusam os números; falhou, cai no chat (montagem).
- Update detectável segue o gatilho graduado do preflight (#174); nunca "em dia" sem comparar; update que não se aplica sozinho não trava o briefing.

## Resultado esperado

Panorama numerado único em dois tempos (local 1..k → emails e agenda k+1..N), proposta do dia com opções curtas, curadoria `Responder`/`Ver`/`Sem ação` com P1/P2/P3, fechamento com escrita nos canais.
