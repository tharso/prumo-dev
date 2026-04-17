# Briefing Procedure

> **module_version: 4.17.0**
>
> Fonte canônica do procedimento de `/prumo:briefing`.
> Se este módulo conflitar com um resumo em `SKILL.md`, este módulo vence.
> Se este módulo conflitar com um `ASSERT:` do `.prumo/system/PRUMO-CORE.md`, o `ASSERT:` vence.
>
> Este módulo é o procedimento do bundled Cowork, com detalhes de bridge e fallback específicos desse host.

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

## Passo 0: Bridge experimental do runtime local

Antes de montar o briefing legado dentro do host:

1. Se houver shell e o workspace expuser `AGENT.md` + `.prumo/state/workspace-schema.json`, tentar o procedimento de `cowork-runtime-bridge.md`.
2. Se o bridge devolver saída com código `0`, usar essa saída como briefing final e encerrar.
3. Se o bridge devolver `12`, seguir silenciosamente para o briefing legado.
4. Se o bridge falhar por outro motivo, registrar isso em uma linha curta e seguir.

O objetivo aqui não é heroísmo. É só deixar o Cowork fazer papel de interface quando o runtime novo já estiver de pé.

## Passo 1: Configuração e data local

1. Extrair timezone do `Prumo/Agente/PERFIL.md` (default: `America/Sao_Paulo`).
2. Resolver data local por fonte verificável:
   - ferramenta de tempo com timezone;
   - relógio do sistema com TZ explícito;
   - APIs de calendário no mesmo fuso.
3. Se não houver fonte confiável, não anunciar dia/data textual no cabeçalho.
4. Se `Prumo/Agente/PERFIL.md` ou `.prumo/system/PRUMO-CORE.md` não existirem, interromper e orientar o usuário a rodar o setup.

## Passo 2: Preflight de versão

Antes do panorama, o briefing deve tentar checar atualização do Prumo.

1. Comparar a versão local usando o módulo `version-update.md`.
2. Se houver versão nova detectável:
   - parar antes do panorama;
   - avisar a diferença de versão;
   - dizer se existe ou não transporte seguro de aplicação;
   - oferecer alternativas curtas para o usuário responder.
3. Quando houver escolha, usar algo como:
   - `a) atualizar agora`
   - `b) seguir mesmo assim`
   - `c) ver diagnóstico`
4. Se não houver transporte seguro de aplicação:
   - avisar a limitação;
   - não bloquear o briefing;
   - permitir seguir com `b)`.
5. Se `Prumo/VERSION` local for maior que o `prumo_version` do `.prumo/system/PRUMO-CORE.md` do workspace:
   - tratar isso como motor do workspace defasado;
   - avisar explicitamente antes do panorama;
   - não fingir briefing normal em cima de core velho.
6. Se a checagem falhar, registrar em uma linha e seguir. O briefing não pode virar refém de updater manco.

## Passo 3: Estado operacional

1. Ler `PAUTA.md`.
2. Ler `INBOX.md`.
3. Se existir `.prumo/state/auto-sanitize-state.json`, usar como telemetria de manutenção.
4. Se existir `.prumo/state/briefing-state.json`:
   - capturar em memória o `last_briefing_at` anterior antes de qualquer escrita nova;
   - se houver `interrupted_at` + `resume_point` no mesmo dia local, oferecer `a) retomar` ou `b) recomeçar`;
   - se `interrupted_at` for de dia anterior, expirar silenciosamente.
5. Janela temporal de email:
   - usar o `last_briefing_at` anterior quando existir;
   - sem esse estado, usar fallback de 24h.

## Passo 4: Canais de entrada e fontes primárias

### 3.1 Autosanitização preventiva

Quando houver shell, tentar manutenção preventiva via `prumo_auto_sanitize.py`. Se falhar, registrar em uma linha e seguir. Os paths válidos do script são definidos em `runtime-paths.md`.

### 3.2 Inbox4Mobile

Se houver `Inbox4Mobile/`, delegar a triagem para:

- `skills/prumo/references/modules/inbox-processing.md`

Esse módulo é a fonte canônica de preview, commit, `_processed.json`, deleção e roteamento.

### 3.3 Email e calendário via MCP direto

Usar integração nativa de Gmail MCP e Calendar MCP como fonte primária.

#### Taxonomia de prioridade

- **P1 — Ação necessária hoje.** Deadline iminente, blocker, resposta esperada por alguém, decisão pendente. Se não tratar hoje, tem consequência concreta.
- **P2 — Ação necessária esta semana.** Importante mas não urgente. Pode esperar o próximo briefing sem consequência.
- **P3 — Informativo.** Vale saber que existe, mas não exige ação. Newsletter relevante, notificação de status, FYI.

#### Janela temporal

- `last_briefing_at` anterior, quando existir;
- fallback de 24h quando não existir.
- Usar formato `after:YYYY/MM/DD` na query do Gmail MCP.

#### Pipeline de curadoria em camadas

Antes de executar as queries, ler `Prumo/Referencias/EMAIL-CURADORIA.md` (se existir) para carregar regras aprendidas, remetentes conhecidos e patterns de exclusão/inclusão.

**Camada 1 — Canal prioritário (P1 automático):**
```
label:Prumo after:{last_briefing_date}
```
```
(subject:PRUMO OR subject:INBOX:) after:{last_briefing_date}
```
Tudo que chega por esses canais é P1 e entra direto no briefing.

**Camada 2 — Emails diretos e threads ativas:**
```
is:unread after:{last_briefing_date}
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

## Passo 5: Persistir início do briefing

Antes da primeira resposta com panorama + proposta:

1. Persistir `.prumo/state/briefing-state.json` com `last_briefing_at` no timestamp ISO local atual.
2. Limpar `interrupted_at` e `resume_point`.
3. Com shell, preferir `prumo_briefing_state.py`.
4. Sem shell, escrever o JSON diretamente.
5. Validar a escrita antes de responder.

Sem essa persistência, o briefing não está oficialmente aberto.

## Passo 6: Montar o briefing progressivo

### Bloco 1 — Panorama

Entregar automaticamente:

1. abertura com data correta no fuso do usuário;
2. agenda do dia, consolidada por conta quando aplicável;
3. link para `Inbox4Mobile/inbox-preview.html` quando `_preview-index.json` existir;
4. contagem silenciosa de agendados.

**Numeração:** cada email, evento de calendário, pendência e item de inbox é um item numerado sequencial. A contagem começa em 1 no primeiro item do briefing e nunca reinicia (ver REGRA DE NUMERAÇÃO no topo deste módulo).

Na primeira resposta do briefing, é proibido abrir arquivos brutos de `Inbox4Mobile/*` (preferir sempre `_preview-index.json` se existir).

### Bloco 2 — Proposta do dia

Oferecer exatamente:

- `a) Aceitar e seguir`
- `b) Ajustar`
- `c) Ver lista completa`
- `d) Tá bom por hoje`

A proposta deve considerar:

1. deadlines de hoje;
2. blockers;
3. agenda disponível;
4. itens com cobrança elegível hoje.
5. alternativas respondíveis em `a)`, `b)`, `c)`, `d)`.

### Contexto completo sob demanda

Se o usuário pedir `c` ou chamar `/prumo:briefing --detalhe`:

1. mostrar andamento, atrasados/parados (`desde DD/MM`), agendados da semana e cobranças elegíveis;
2. manter lista numerada contínua;
3. não resetar o briefing nem as opções.

## Passo 7: Escape hatch

Se o usuário disser `tá bom por hoje`, `escape`, `depois` ou equivalente:

1. manter `last_briefing_at` já gravado no início;
2. gravar `interrupted_at`;
3. gravar `resume_point`;
4. encerrar sem cobrança adicional.

No mesmo dia local, a próxima chamada a `/prumo:briefing` deve oferecer retomada. Em dia seguinte, o estado expira silenciosamente.

## Passo 8: Escrita e fechamento

Depois do briefing:

1. atualizar `PAUTA.md` se algo mudou;
2. registrar ações no `REGISTRO.md`;
3. manter `Inbox4Mobile/_processed.json` sincronizado quando houver fallback sem deleção física.

Se o briefing concluiu normalmente:

1. garantir que `interrupted_at` e `resume_point` não existam;
2. não sobrescrever a janela anterior em memória usada na própria sessão.

## Passo 9: Brain dump obrigatório quando a pauta estiver vazia

Se `PAUTA.md` estiver vazia ou quase vazia, não fingir briefing normal. Pedir dump fresco do usuário.
