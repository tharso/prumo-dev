# Briefing Procedure

> **module_version: 4.21.0**
>
> Fonte canônica do procedimento de briefing do Prumo.
> Se este módulo conflitar com um resumo em `SKILL.md`, este módulo vence.
> Se este módulo conflitar com um `ASSERT:` do `.prumo/system/PRUMO-CORE.md`, o `ASSERT:` vence.

## REGRA DE NUMERAÇÃO (obrigatória, sem exceção)

Todo item acionável do briefing recebe um número sequencial único, do primeiro ao último, sem reiniciar entre seções. Se há 5 emails, 3 eventos de calendário e 4 pendências, os números vão de 1 a 12. Emails: 1-5. Agenda: 6-8. Pendências: 9-12. Isso permite ao usuário responder "3, 7, 12" para despachar múltiplos itens de uma vez.

Nunca reiniciar a contagem ao mudar de seção. Nunca usar sub-numeração (1.1, 1.2). Nunca omitir a numeração em itens que pedem decisão ou atenção.

## Pré-carga obrigatória

Antes de executar o briefing:

1. Ler `Prumo/Agente/PERFIL.md`.
2. Ler `.prumo/system/PRUMO-CORE.md`.
3. Ler `skills/prumo/references/modules/load-policy.md` quando o repo local estiver disponível.
4. Ler `skills/prumo/references/modules/version-update.md`.
5. Ler `skills/prumo/references/modules/runtime-paths.md` quando houver shell.

## Passo 0: tentar o runtime primeiro

Antes de montar o briefing manualmente:

1. Se houver `prumo` no PATH e o workspace expuser `AGENT.md` + `.prumo/state/workspace-schema.json`, rodar `prumo briefing --workspace <path>`.
2. Se o runtime devolver saída com código `0`, entregar essa saída como briefing final e encerrar.
3. Se o runtime falhar, registrar em uma linha curta e seguir para o fluxo manual abaixo.

O objetivo aqui não é heroísmo. Quando o runtime responde, ele é o caminho determinístico e a skill só serve como contrato. Quando não responde, o agente cumpre o contrato manualmente.

## Passo 1: configuração e data local

1. Extrair timezone do `Prumo/Agente/PERFIL.md` (default: `America/Sao_Paulo`).
2. Resolver data local por fonte verificável:
   - ferramenta de tempo com timezone;
   - relógio do sistema com TZ explícito;
   - APIs de calendário no mesmo fuso.
3. Se não houver fonte confiável, não anunciar dia/data textual no cabeçalho.
4. Se `Prumo/Agente/PERFIL.md` ou `.prumo/system/PRUMO-CORE.md` não existirem, interromper e orientar o usuário a rodar o setup.

## Passo 2: preflight de versão

Antes do panorama, comparar a versão local usando o módulo `version-update.md`.

1. Se houver versão nova detectável, avisar a diferença em uma linha e seguir o briefing. Não bloquear.
2. Se `Prumo/VERSION` local for maior que o `prumo_version` do `.prumo/system/PRUMO-CORE.md` do workspace, avisar que o core do workspace está defasado e seguir.
3. Se a checagem falhar, registrar em uma linha e seguir. O briefing não vira refém de updater manco.

## Passo 3: estado operacional

1. Ler `PAUTA.md`.
2. Ler `INBOX.md`.

Não persistir estado de briefing entre sessões. A janela temporal de email é fixa em 24h (ver Passo 4).

## Passo 4: canais de entrada

### Inbox4Mobile

Se houver `Inbox4Mobile/`, delegar a triagem para:

- `skills/prumo/references/modules/inbox-processing.md`

Esse módulo é a fonte canônica de preview, commit, `_processed.json`, deleção e roteamento.

### Email e calendário via MCP direto

Usar integração nativa de Gmail MCP e Calendar MCP como fonte primária.

#### Taxonomia de prioridade

- **P1 — Ação necessária hoje.** Deadline iminente, blocker, resposta esperada por alguém, decisão pendente. Se não tratar hoje, tem consequência concreta.
- **P2 — Ação necessária esta semana.** Importante mas não urgente. Pode esperar o próximo briefing sem consequência.
- **P3 — Informativo.** Vale saber que existe, mas não exige ação. Newsletter relevante, notificação de status, FYI.

#### Janela temporal

- Fixa em 24h: usar `after:YYYY/MM/DD` na query do Gmail MCP, com a data de ontem no fuso local.

#### Pipeline de curadoria em camadas

Antes de executar as queries, ler `Prumo/Referencias/EMAIL-CURADORIA.md` (se existir) para carregar regras aprendidas, remetentes conhecidos e patterns de exclusão/inclusão.

**Camada 1 — Canal prioritário (P1 automático):**
```
label:Prumo after:{ontem}
```
```
(subject:PRUMO OR subject:INBOX:) after:{ontem}
```
Tudo que chega por esses canais é P1 e entra direto no briefing.

**Camada 2 — Emails diretos e threads ativas:**
```
is:unread after:{ontem}
```
A inbox agrega 4 contas (tharso@gmail.com, tharso@brise.cloud, tharso@brise.science, tharso@tharso.com). Uma query cobre todas. Emails em CC/BCC são válidos quando vêm de pessoas reais.

**Filtragem em dois estágios:**

*Estágio 1 — Metadata (rápido, sem ler corpo):*
Eliminar por padrão de remetente: `noreply@`, `no-reply@`, `notifications@`, `mailer-daemon@`, `marketing@`, `news@`, `updates@`, e patterns de serviço automatizado. Consultar `EMAIL-CURADORIA.md` para regras aprendidas (remetentes marcados como ruído ou como sempre-relevante).

*Estágio 2 — Leitura seletiva (só emails que passaram o estágio 1):*
Ler o corpo via `gmail_read_message`. Cruzar com contexto vivo:
- Ler `Prumo/PAUTA.md` para saber o que está quente.
- Usar o conhecimento de `Prumo/Agente/PERFIL.md` (áreas, projetos ativos, pessoas).
- Se o email se relaciona com algo da pauta ou de um projeto ativo, sobe de prioridade.
- Exemplo: email do contador é P1 se há item de CNPJ na pauta. Newsletter sobre IA é P3 mas sobe pra P2 se o usuário está escrevendo artigo sobre o tema.

**Camada 3 — Roteamento de conteúdo:**
Se o email é conteúdo pra consumir (artigo, vídeo, podcast, thread, newsletter curada), rotear para `Projetos/Revue/INBOX_Revue/` em vez de tratar como email de ação. Marcar como roteado no briefing mas não cobrar ação.

#### Classificação final

Classificar cada email que passou a filtragem em:
- `Responder` — exige resposta escrita do usuário.
- `Ver` — exige leitura ou ciência, mas não resposta.
- `Sem ação` — informativo puro, pode só ser mencionado.

Atribuir P1/P2/P3 com motivo objetivo em uma frase curta. Cada email é um item numerado (ver REGRA DE NUMERAÇÃO no topo deste módulo).

#### Feedback loop

Quando o usuário corrigir a curadoria ("esse era ruído", "faltou aquele email do fulano", "isso não era P1"):
1. Registrar a regra em `Prumo/Referencias/EMAIL-CURADORIA.md`.
2. Formato: data, remetente/pattern, regra aprendida, motivo.
3. Viés explícito: na dúvida, trazer. Melhor ruído que perda.

Se `EMAIL-CURADORIA.md` não existir, criar com estrutura:
```markdown
# Curadoria de email — regras aprendidas

> Atualizado pelo agente com feedback do usuário.
> Consultado a cada briefing antes de filtrar emails.

## Remetentes sempre relevantes
(lista vazia até primeiro feedback)

## Remetentes sempre ruído
(lista vazia até primeiro feedback)

## Regras contextuais
(lista vazia até primeiro feedback)

## Log de feedback
(entradas com data, o que aconteceu, regra derivada)
```

#### Calendário

Consolidar agenda por conta quando houver mais de um calendário. Cada evento do dia é um item numerado (continuar da numeração dos emails).

## Passo 5: montar o briefing

Entregar em uma resposta única, numerada de 1 a N:

1. Abertura com data correta no fuso do usuário.
2. Agenda do dia, consolidada por conta quando aplicável.
3. Emails curados (Camadas 1, 2 e 3 aplicadas), com classificação Responder/Ver/Sem ação e prioridade P1/P2/P3.
4. Pendências vivas de `PAUTA.md` (quente, em andamento, agendado).
5. Link para `Inbox4Mobile/inbox-preview.html` quando `_preview-index.json` existir. Na primeira resposta do briefing é proibido abrir arquivos brutos de `Inbox4Mobile/*`; preferir sempre `_preview-index.json`.

Depois da lista numerada, entregar a proposta do dia em uma linha curta e oferecer opções respondíveis:

- `a) Aceitar e seguir`
- `b) Ajustar`
- `c) Ver lista completa`
- `d) Tá bom por hoje`

A proposta deve considerar deadlines de hoje, blockers, agenda disponível e itens com cobrança elegível hoje.

## Passo 6: escrita e fechamento

Depois do briefing:

1. Atualizar `PAUTA.md` se algo mudou.
2. Registrar ações no `REGISTRO.md`.
3. Manter `Inbox4Mobile/_processed.json` sincronizado quando houver fallback sem deleção física.

## Passo 7: brain dump obrigatório quando a pauta estiver vazia

Se `PAUTA.md` estiver vazia ou quase vazia, não fingir briefing normal. Pedir dump fresco do usuário.
