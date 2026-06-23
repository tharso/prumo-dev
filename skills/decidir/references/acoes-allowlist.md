# Allowlist de ações por tipo de item

O Prumo **seleciona** ações desta lista — não inventa verbos. Ações inconsistentes entre execuções confundem o usuário e quebram a previsibilidade do despacho. Se um item não cabe em nenhum tipo abaixo, prefira o tipo mais próximo e ofereça só as ações que fazem sentido para aquele item específico.

Cada ação tem:

- **`key`** — id do botão (snake_case, não traduzir). É o que o usuário escolhe e o que vai no JSON como `action_key`.
- **`label`** — o texto do botão (PT, é o que o usuário vê).
- **`tone`** — cor do botão: `green` (avançar), `amber` (adiar/cautela), `red` (risco/remoção), `blue` (rotear/secundária), `slate` (neutra).
- **`effect`** — **token canônico (snake_case) do que o Prumo executa** ao receber o relatório. É um enum estável, não prosa — o agente lê o `effect` do JSON e age. Use exatamente os tokens desta tabela; não invente nem descreva em prosa no campo `effect`.
- **`requires`** — detalhe que o **comentário** precisa trazer (o usuário preenche). Se preenchido, marque o botão (`⚑`) e, ao receber o relatório com `requires_missing`, peça o detalhe antes de executar.
- **`confirma?`** — se o `effect` precisa de confirmação extra apesar da promessa "executo sem perguntar de novo".

## Regra de ouro da execução

Tokens `draft_*` produzem **rascunho** (não enviam). "Executo sem perguntar de novo" vale para `draft_*`, registrar, `mark_seen`, `make_task`/`make_reference`/`make_pauta`, `snooze`/`wait_until`/`promote_today`, e `archive` **com destino explícito**. **NÃO** vale (confirma antes) para enviar de fato o que foi rascunhado, `rsvp_decline`/`propose_reschedule` com terceiros, e qualquer remoção de inbox (`archive`/`discard`) — o core exige confirmar o plano e registrar no `REGISTRO.md` antes de remover o original. Botão não é procuração vitalícia.

## Por tipo

### Email que pede resposta

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Responder | `reply` | green | `draft_reply` | o que responder | só ao enviar |
| Ver/Marcar visto | `mark_seen` | slate | `mark_seen` | — | não |
| Arquivar | `archive` | slate | `archive` | destino se arquivo local | sim p/ inbox/local |
| Adiar | `snooze` | amber | `snooze` | até quando | não |
| Delegar | `delegate` | blue | `draft_delegation` | destinatário | só ao enviar |
| Sem ação | `no_action` | slate | `no_action` | — | não |

### Email informativo

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Ver/Marcar visto | `mark_seen` | slate | `mark_seen` | — | não |
| Rotear p/ leitura | `route_reading` | blue | `route_reading` | — | não |
| Arquivar | `archive` | slate | `archive` | — | não |
| Sem ação | `no_action` | slate | `no_action` | — | não |

### Evento de calendário (do dia, sem RSVP)

O calendário do briefing é "evento do dia", não necessariamente convite. Sem RSVP, `Confirmar/Recusar` não fazem sentido.

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Preparar | `prepare` | green | `prepare` | o que preparar | não |
| Virar tarefa | `make_task` | blue | `make_task` | — | não |
| Remarcar | `calendar_reschedule` | amber | `propose_reschedule` | novo horário | sim se há terceiros |
| Sem ação | `no_action` | slate | `no_action` | — | não |

### Convite de calendário (com RSVP)

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Confirmar | `calendar_accept` | green | `rsvp_accept` | — | não, se o evento exato está no card |
| Recusar | `calendar_decline` | red | `rsvp_decline` | motivo se há mensagem | sim se há mensagem aos convidados |
| Remarcar | `calendar_reschedule` | amber | `propose_reschedule` | novo horário | sim se há terceiros |
| Delegar | `delegate` | blue | `draft_delegation` | destinatário | só ao enviar |

### Pendência / cobrança

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Fazer hoje | `do_today` | green | `promote_today` | — | não |
| Aguardar até | `wait_until` | blue | `wait_until` | nova data | não |
| Cobrar | `follow_up` | amber | `draft_follow_up` | canal e o que pedir | só ao enviar |
| Delegar | `delegate` | blue | `draft_delegation` | destinatário | só ao enviar |
| Descartar | `discard` | red | `discard` | motivo | sim (remoção) |

### Item de inbox (conteúdo / arquivo / link)

Inbox4Mobile traz conteúdo, não nota pura. Remoção sempre confirma (ASSERT do core: confirmar plano + registrar no `REGISTRO.md` antes de remover o original).

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Rotear p/ leitura | `route_reading` | blue | `route_reading` | — | não |
| Virar referência | `make_reference` | green | `save_reference` | onde guardar | não |
| Virar tarefa | `make_task` | blue | `make_task` | — | não |
| Arquivar | `archive` | slate | `archive` | — | sim (remoção de inbox) |
| Descartar | `discard` | red | `discard` | motivo | sim (remoção de inbox) |

### Decisão entre alternativas

Não é card de despacho — é card `escolha` (A/B/C com texto final e uma `rec: true`). Cada opção pode trazer um `effect` próprio para o Prumo executar a escolha (ex.: `focus_acme`); aqui o token é livre porque descreve a decisão específica, não uma ação genérica do catálogo.

## Sobre `key` vs `effect`

`key` é a escolha do usuário (botão); `effect` é o que o Prumo executa. Costumam coincidir, mas divergem quando o botão "esconde" a semântica de máquina — ex.: `Responder` (`key: reply`) produz `effect: draft_reply` (rascunho, não envio). O JSON do relatório carrega os dois; o agente decide pela `effect`.
