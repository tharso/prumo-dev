# Allowlist de ações por tipo de item

O Prumo **seleciona** ações desta lista — não inventa verbos. Ações inconsistentes entre execuções confundem o usuário e quebram a previsibilidade do despacho. Se um item não cabe em nenhum tipo abaixo, prefira o tipo mais próximo e ofereça só as ações que fazem sentido para aquele item específico.

Cada ação tem:

- **`key`** — identificador estável (não traduzir; é o que vai no JSON).
- **`label`** — o texto do botão (PT, é o que o usuário vê).
- **`tone`** — cor do botão: `green` (ação positiva/avançar), `amber` (adiar/cautela), `red` (risco/remoção), `blue` (rotear/secundária), `slate` (neutra).
- **`effect`** — o que o Prumo executa ao receber o relatório.
- **`requires`** — detalhe que o comentário precisa trazer; se vazio, a ação executa sem detalhe. Marque o botão com `requires` para o usuário ver o ⚑.
- **`confirma?`** — se o `effect` precisa de confirmação extra apesar da promessa "executo sem perguntar de novo".

## Regra de ouro da execução

"Executo sem perguntar de novo" vale para **rascunhar, registrar, marcar visto, virar pauta/tarefa, adiar, arquivar com destino explícito**. **NÃO** vale (confirma antes) para **enviar email/cobrança de fato, recusar/remarcar com terceiros, e qualquer remoção de item de inbox** — o core exige confirmar o plano e registrar no `REGISTRO.md` antes de remover o original. Botão não é procuração vitalícia.

## Por tipo

### Email que pede resposta

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Responder | `reply` | green | rascunho de resposta (não envia) | o que responder | só se for enviar de fato |
| Ver/Marcar visto | `mark_seen` | slate | registra ciência; marca lido se possível | — | não |
| Arquivar | `archive` | slate | arquiva/move processado | destino se arquivo local | sim p/ remoção de inbox/local |
| Adiar | `snooze` | amber | reagenda retomada (marker `cobrar: DD/MM`) | até quando | não |
| Delegar | `delegate` | blue | rascunho de delegação (não envia) | destinatário | só se for enviar |
| Sem ação | `no_action` | slate | registra que não exige ação | — | não |

### Email informativo

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Ver/Marcar visto | `mark_seen` | slate | registra ciência | — | não |
| Rotear p/ leitura | `route_reading` | blue | move/registra em fila de leitura | — | não |
| Arquivar | `archive` | slate | arquiva | — | não |
| Sem ação | `no_action` | slate | registra ciência sem promover | — | não |

### Evento de calendário (do dia, sem RSVP)

O calendário do briefing é "evento do dia", não necessariamente convite. Sem RSVP, `Confirmar/Recusar` não fazem sentido.

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Preparar | `prepare` | green | cria nota/checklist de preparo | o que preparar | não |
| Virar tarefa | `make_task` | blue | cria item em `PAUTA.md` | — | não |
| Remarcar | `calendar_reschedule` | amber | propõe novo horário/altera evento | novo horário | sim se há terceiros |
| Sem ação | `no_action` | slate | registra ciência | — | não |

### Convite de calendário (com RSVP)

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Confirmar | `calendar_accept` | green | RSVP "sim" | — | não, se o evento exato está no card |
| Recusar | `calendar_decline` | red | RSVP "não" | motivo se há mensagem | sim se há mensagem aos convidados |
| Remarcar | `calendar_reschedule` | amber | propõe novo horário | novo horário | sim se há terceiros |
| Delegar | `delegate` | blue | rascunho de delegação | destinatário | só se for enviar |

### Pendência / cobrança

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Fazer hoje | `do_today` | green | promove para foco de hoje / pauta quente | — | não |
| Aguardar até | `wait_until` | blue | mantém fora do briefing até a data; seta cobrança | nova data | não |
| Cobrar | `follow_up` | amber | rascunho de cobrança/follow-up (não envia) | canal e o que pedir | só se for enviar |
| Delegar | `delegate` | blue | rascunho de delegação | destinatário | só se for enviar |
| Descartar | `discard` | red | remove da fila ativa | motivo | sim (remoção) |

### Item de inbox (conteúdo / arquivo / link)

Inbox4Mobile traz conteúdo, não nota pura. Remoção sempre confirma (ASSERT do core: confirmar plano + registrar no `REGISTRO.md` antes de remover o original).

| label | key | tone | effect | requires | confirma? |
|---|---|---|---|---|---|
| Rotear p/ leitura | `route_reading` | blue | move/registra em fila de leitura | — | não |
| Virar referência | `make_reference` | green | guarda como referência no workspace | onde guardar | não |
| Virar tarefa | `make_task` | blue | cria item em `PAUTA.md` | — | não |
| Arquivar | `archive` | slate | arquiva o item | — | sim (remoção de inbox) |
| Descartar | `discard` | red | descarta o item | motivo | sim (remoção de inbox) |

### Decisão entre alternativas

Não é card de despacho — é card `escolha` (A/B/C com texto final e uma `rec: true`). Cada opção pode trazer `effect` para o Prumo executar a escolha (ex.: `focus_acme`).
