# Briefing Procedure

> **module_version: 4.14.1**
>
> Fonte canônica do procedimento de `/prumo:briefing`.
> Se este módulo conflitar com um resumo em `SKILL.md`, este módulo vence.
> Se este módulo conflitar com um `ASSERT:` do `PRUMO-CORE.md`, o `ASSERT:` vence.

## Pré-carga obrigatória

Antes de executar o briefing:

1. Ler `CLAUDE.md`.
2. Ler `PRUMO-CORE.md`.
3. Ler `Prumo/cowork-plugin/skills/prumo/references/modules/load-policy.md` quando o repo local estiver disponível.
4. Ler `Prumo/cowork-plugin/skills/prumo/references/modules/version-update.md`.
5. Ler `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-paths.md` quando houver shell.

## Passo 0: Bridge experimental do runtime local

Antes de montar o briefing legado dentro do host:

1. Se houver shell e o workspace expuser `AGENT.md` + `_state/workspace-schema.json`, tentar o procedimento de `cowork-runtime-bridge.md`.
2. Se o bridge devolver saída com código `0`, usar essa saída como briefing final e encerrar.
3. Se o bridge devolver `12`, seguir silenciosamente para o briefing legado.
4. Se o bridge falhar por outro motivo, registrar isso em uma linha curta e seguir.

O objetivo aqui não é heroísmo. É só deixar o Cowork fazer papel de interface quando o runtime novo já estiver de pé.

## Passo 1: Configuração e data local

1. Extrair timezone do `CLAUDE.md` (default: `America/Sao_Paulo`).
2. Resolver data local por fonte verificável:
   - ferramenta de tempo com timezone;
   - relógio do sistema com TZ explícito;
   - APIs de calendário no mesmo fuso.
3. Se não houver fonte confiável, não anunciar dia/data textual no cabeçalho.
4. Se `CLAUDE.md` ou `PRUMO-CORE.md` não existirem, interromper e orientar o usuário a rodar o setup.

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
5. Se `Prumo/VERSION` local for maior que o `prumo_version` do `PRUMO-CORE.md` do workspace:
   - tratar isso como motor do workspace defasado;
   - avisar explicitamente antes do panorama;
   - não fingir briefing normal em cima de core velho.
6. Se a checagem falhar, registrar em uma linha e seguir. O briefing não pode virar refém de updater manco.

## Passo 3: Estado operacional

1. Ler `PAUTA.md`.
2. Ler `INBOX.md`.
3. Verificar handovers:
   - preferir `_state/HANDOVER.summary.md`;
   - fallback para `_state/HANDOVER.md`;
   - destacar itens `PENDING_VALIDATION` e `REJECTED`.
4. Se existir `_state/auto-sanitize-state.json`, usar como telemetria de manutenção.
5. Se existir `_state/briefing-state.json`:
   - capturar em memória o `last_briefing_at` anterior antes de qualquer escrita nova;
   - se houver `interrupted_at` + `resume_point` no mesmo dia local, oferecer `a) retomar` ou `b) recomeçar`;
   - se `interrupted_at` for de dia anterior, expirar silenciosamente.
6. Janela temporal de email:
   - usar o `last_briefing_at` anterior quando existir;
   - sem esse estado, usar fallback de 24h.

## Passo 4: Canais de entrada e fontes primárias

### 3.1 Autosanitização preventiva

Quando houver shell, tentar manutenção preventiva via `prumo_auto_sanitize.py`. Se falhar, registrar em uma linha e seguir. Os paths válidos do script são definidos em `runtime-paths.md`.

### 3.2 Inbox4Mobile

Se houver `Inbox4Mobile/`, delegar a triagem para:

- `Prumo/cowork-plugin/skills/prumo/references/modules/inbox-processing.md`

Esse módulo é a fonte canônica de preview, commit, `_processed.json`, deleção e roteamento.

### 3.3 Snapshots no Google Drive (fonte primária)

Antes de qualquer fallback de Gmail/Calendar:

1. Buscar Google Docs `Prumo/snapshots/email-snapshot` das contas conectadas via MCP Google Drive.
2. Ler o texto de cada Doc.
3. Parsear o JSON contido no texto.
4. Tratar cada snapshot como fonte por conta (`pessoal`/`trabalho`) para agenda e emails crus.
5. Validar `generated_at`:
   - se estiver acima de 30 minutos, usar mesmo assim e avisar explicitamente a defasagem;
   - se a leitura exceder 45 segundos no total, seguir para fallback sem bloquear o briefing.
6. Respeitar o `since` gravado no próprio snapshot. Não recalcular essa janela por cima.
7. Se houver `emails_error` ou `calendar_error`, preservar dados parciais e reportar o erro em uma linha.
8. Curadoria continua no Prumo:
   - classificar emails em `Responder`, `Ver` e `Sem ação`;
   - atribuir `P1/P2/P3` com motivo objetivo;
   - consolidar agenda por conta.

### 3.4 Fallback com shell

Se os snapshots estiverem ausentes, inválidos ou inacessíveis e houver shell:

1. Tentar `scripts/prumo_google_dual_snapshot.sh`.
2. Usar a saída como fonte principal para agenda e triagem das contas `pessoal` e `trabalho`.
3. Respeitar a janela temporal reportada pelo próprio script.
4. Se uma conta falhar, manter a outra e avisar objetivamente.

Os paths válidos do script são definidos em `runtime-paths.md`.

### 3.5 Fallback sem shell

Se não houver snapshot válido e o script dual não puder rodar:

1. Usar integração nativa de Gmail/Calendar.
2. Janela de email:
   - `last_briefing_at` anterior, quando existir;
   - fallback de 24h quando não existir.
3. Manter a mesma taxonomia:
   - `Responder`
   - `Ver`
   - `Sem ação`
   - `P1/P2/P3`

## Passo 5: Persistir início do briefing

Antes da primeira resposta com panorama + proposta:

1. Persistir `_state/briefing-state.json` com `last_briefing_at` no timestamp ISO local atual.
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
4. contagem silenciosa de agendados;
5. pendências de handover em uma linha objetiva.
6. numeração contínua mesmo ao passar do panorama para proposta e detalhe.

Na primeira resposta do briefing, é proibido abrir arquivos brutos de `Inbox4Mobile/*`.

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
3. atualizar `_state/HANDOVER.md` se houve validação;
4. manter `Inbox4Mobile/_processed.json` sincronizado quando houver fallback sem deleção física.

Se o briefing concluiu normalmente:

1. garantir que `interrupted_at` e `resume_point` não existam;
2. não sobrescrever a janela anterior em memória usada na própria sessão.

## Passo 9: Brain dump obrigatório quando a pauta estiver vazia

Se `PAUTA.md` estiver vazia ou quase vazia, não fingir briefing normal. Pedir dump fresco do usuário.
