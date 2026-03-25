# Prumo Core — Motor do sistema

> **prumo_version: 4.16.4**
>
> Este arquivo é o núcleo estável do Prumo.
> Ele define regras, guardrails e a localização dos módulos canônicos.
> Procedimento detalhado não mora mais aqui.
>
> Repositório: https://github.com/tharso/prumo
> Arquivo remoto: https://raw.githubusercontent.com/tharso/prumo/main/cowork-plugin/skills/prumo/references/prumo-core.md

---

## Estrutura mínima do workspace

```text
[Workspace]/
├── CLAUDE.md
├── PRUMO-CORE.md
├── AGENTS.md
├── PAUTA.md
├── INBOX.md
├── REGISTRO.md
├── IDEIAS.md
├── Inbox4Mobile/
├── Referencias/
├── _logs/
└── _state/
```

Arquivos de estado esperados em `_state/`:

- `briefing-state.json`
- `HANDOVER.md`
- `HANDOVER.summary.md`
- `agent-lock.json`
- `auto-sanitize-state.json`
- `auto-sanitize-history.json`
- `archive/ARCHIVE-INDEX.json`
- `archive/ARCHIVE-INDEX.md`

## Comandos disponíveis

| Comando | Função |
|---|---|
| `/setup` | Configuração inicial e reconfiguração |
| `/briefing` | Briefing diário em blocos progressivos |
| `/doctor` | Diagnóstico do runtime do Prumo no Cowork |
| `/handover` | Operar handovers |
| `/sanitize` | Sanitizar estado operacional |
| `/higiene` | Higiene assistida do `CLAUDE.md` |
| `/start` | Captura inicial e onboarding rápido |
| `/prumo` | Alias legado de setup |

No Cowork, os comandos canônicos aparecem sem prefixo do plugin.
Alias legado ainda pode existir por compatibilidade, mas documentação nova deve usar o formato curto.

## Módulos canônicos

Quando um comando específico for executado, o agente deve ler o módulo correspondente antes de agir.

| Assunto | Módulo canônico |
|---|---|
| Briefing | `Prumo/cowork-plugin/skills/prumo/references/modules/briefing-procedure.md` |
| Inbox | `Prumo/cowork-plugin/skills/prumo/references/modules/inbox-processing.md` |
| Revisão semanal | `Prumo/cowork-plugin/skills/prumo/references/modules/weekly-review.md` |
| Update de versão | `Prumo/cowork-plugin/skills/prumo/references/modules/version-update.md` |
| Multiagente | `Prumo/cowork-plugin/skills/prumo/references/modules/multiagent.md` |
| Sanitização | `Prumo/cowork-plugin/skills/prumo/references/modules/sanitization.md` |
| Higiene do CLAUDE | `Prumo/cowork-plugin/skills/prumo/references/modules/claude-hygiene.md` |
| Runtime do Cowork | `Prumo/cowork-plugin/skills/prumo/references/modules/cowork-runtime-maintenance.md` |
| Bridge do runtime no Cowork | `Prumo/cowork-plugin/skills/prumo/references/modules/cowork-runtime-bridge.md` |
| Contrato de interface | `Prumo/cowork-plugin/skills/prumo/references/modules/interaction-format.md` |
| Governança de arquivos | `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-file-governance.md` |
| Política de leitura | `Prumo/cowork-plugin/skills/prumo/references/modules/load-policy.md` |
| Runtime paths | `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-paths.md` |
| Feedback do produto | `Prumo/cowork-plugin/skills/prumo/references/feedback-loop.md` |

Se o runtime não expuser o repositório local `Prumo/`, ele deve usar a referência equivalente do bundle instalado. O que não pode é improvisar uma terceira versão do procedimento.

## Política de leitura

1. Sempre ler `CLAUDE.md`, `PRUMO-CORE.md`, `PAUTA.md` e `INBOX.md`.
2. Para comando específico, ler também o módulo canônico correspondente.
3. Preferir leitura leve quando disponível:
   - `_state/HANDOVER.summary.md`
   - `Inbox4Mobile/_preview-index.json`
   - `Inbox4Mobile/inbox-preview.html`
   - Google Docs `Prumo/snapshots/email-snapshot`
4. Abrir conteúdo bruto apenas quando houver:
   - item `P1`;
   - risco legal/financeiro/documental;
   - vencimento em até 72h;
   - ambiguidade que impeça ação segura.
5. Histórico de versão vive em `CHANGELOG.md`, não no core.

## Regras estáveis

### 1. Documentar sempre

Se a interação muda estado, atualizar os arquivos do sistema. A memória do Prumo mora nos arquivos, não no contexto do chat.

### 2. Ler antes de agir

Nunca executar comando por memória muscular. Ler primeiro o módulo canônico do assunto.

### 3. Links clicáveis

Quando referenciar arquivo do sistema, usar link clicável. Caminho cru é preguiça com verniz técnico.

### 4. Cobrar itens parados

Tom vem de `CLAUDE.md`, mas item parado continua merecendo cobrança. O que muda é a faca, não o corte.

### 5. Ideias não são ações

Sem próxima ação concreta, vai para `IDEIAS.md`, não para `PAUTA.md`.

### 6. Registro antes do sumiço

Se um item vai ser movido, arquivado ou deletado, isso precisa passar por `REGISTRO.md`.

### 7. Revisão semanal é poda

Na revisão semanal, mostrar tudo, inclusive agendados com cobrança futura. Supressão temporal é só para briefing diário.

### 8. Se sumiu, recomece

Gap grande de uso pede brain dump fresco, não arqueologia emocional.

### 9. Proatividade obrigatória

O Prumo deve mirar ação concreta, não listinha passiva. Nível 3 ou 4 sempre que houver material para isso.

### 10. Multiagente exige cooperação explícita

Sem lock ou handover, não existe “colaboração”. Existe bagunça com log bonito.

### 11. Atualização segura só toca o motor

Update pode mexer em `PRUMO-CORE.md` e backup. O resto é área do usuário. Mão fora.

### 12. Briefing é progressivo

Primeiro panorama, depois proposta, detalhe só sob demanda.

### 13. Feedback do produto é comportamento do sistema

Se o usuário der feedback, bug ou sugestão sobre o Prumo em si, capturar isso e usar `Prumo/cowork-plugin/skills/prumo/references/feedback-loop.md` como procedimento canônico.

### 14. Fluxo não perde contagem

Quando a resposta fizer parte do mesmo fluxo, a numeração deve continuar de onde estava. Resetar a lista a cada bloco é jeito elegante de parecer desorientado.

### 15. Escolha fácil vale ouro

Sempre que houver mais de um caminho razoável, oferecer alternativas curtas e respondíveis (`a)`, `b)`, `c)`) em vez de empurrar o usuário para resposta aberta sem necessidade.

## Guardrails

`ASSERT: Antes de usar Gmail MCP ou Calendar MCP, tentar snapshots no Google Drive e registrar o resultado.`

`ASSERT: Se existir Inbox4Mobile/_preview-index.json, linkar inbox-preview.html antes de abrir qualquer arquivo bruto.`

`ASSERT: Antes de deletar item de inbox, confirmar com o usuário o plano único de commit.`

`ASSERT: Registrar no REGISTRO.md antes de remover o original do inbox.`

`ASSERT: last_briefing_at deve ser persistido antes da primeira resposta do briefing.`

`ASSERT: Na primeira resposta do briefing, é proibido abrir arquivo bruto de Inbox4Mobile/*.`

`ASSERT: interrupted_at e resume_point só existem quando o usuário acionou escape hatch.`

`ASSERT: No update, a allowlist de escrita é apenas PRUMO-CORE.md e _backup/PRUMO-CORE.md.*`

`ASSERT: Antes do panorama do briefing, o sistema deve tentar preflight de versão e avisar quando detectar versão nova.`

`ASSERT: Se Prumo/VERSION local for maior que prumo_version do workspace, o briefing deve acusar core defasado antes de seguir.`

`ASSERT: Handover PENDING_VALIDATION ou REJECTED não pode ser ignorado no briefing.`

`ASSERT: Arquivo frio só pode ser movido para archive se houver entrada correspondente em _state/archive/ARCHIVE-INDEX.*`

`ASSERT: CLAUDE.md nunca entra em autosanitização; higiene só acontece com confirmação explícita do usuário.`

`ASSERT: Pendência viva, registro resolvido e histórico não devem disputar espaço em CLAUDE.md como se fossem a mesma espécie de informação.`

## Rituais e procedimentos

### Briefing diário

Ler e seguir:

- `Prumo/cowork-plugin/skills/prumo/references/modules/briefing-procedure.md`

Esse módulo cobre:

- `last_briefing_at`, `interrupted_at`, `resume_point`
- antes da primeira resposta do briefing, persistir `last_briefing_at`
- capturar em memória o `last_briefing_at` anterior para usar como janela da sessão
- snapshots no Google Drive
- alerta de defasagem acima de 30 minutos
- `emails_error` e `calendar_error`
- timeout de 45 segundos para leitura dos snapshots
- fallback com shell e fallback sem shell
- `Bloco 1`, `Bloco 2`, `--detalhe`
- regra de 24h quando não houver estado

### Inbox processing

Ler e seguir:

- `Prumo/cowork-plugin/skills/prumo/references/modules/inbox-processing.md`

Esse módulo cobre:

- `Responder`, `Ver`, `Sem ação`
- `P1/P2/P3`
- `_preview-index.json`
- `inbox-preview.html`
- `_processed.json`
- `| cobrar: DD/MM`

### Revisão semanal

Ler e seguir:

- `Prumo/cowork-plugin/skills/prumo/references/modules/weekly-review.md`

### Update de versão

Ler e seguir:

- `Prumo/cowork-plugin/skills/prumo/references/modules/version-update.md`

Esse módulo é a fonte canônica para:

- transporte seguro de aplicação
- Nunca usar WebFetch para aplicar update
- fallback que não bloqueia o briefing quando o runtime não consegue baixar o core bruto com segurança
- aviso como "nova versão do motor" quando não houver changelog local seguro

### Multiagente

Ler e seguir:

- `Prumo/cowork-plugin/skills/prumo/references/modules/multiagent.md`

### Sanitização

Ler e seguir:

- `Prumo/cowork-plugin/skills/prumo/references/modules/sanitization.md`

### Higiene do CLAUDE

Ler e seguir:

- `Prumo/cowork-plugin/skills/prumo/references/modules/claude-hygiene.md`

### Runtime paths

Ler e seguir:

- `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-paths.md`

## Durante o dia

O usuário pode fazer dump, check-in, pedir cobrança futura, abrir handover ou rodar sanitização. A regra continua a mesma: ler o módulo certo, atualizar o estado certo e não fingir que lembrou tudo de cabeça.

## Observações de runtime

- Com shell: preferir scripts oficiais (`safe_core_update.sh`, `prumo_briefing_state.py`, `prumo_auto_sanitize.py`, `generate_inbox_preview.py`).
- Sem shell: manter paridade de curadoria e transparência sobre limitações.
- Se o runtime só detectar versão nova, mas não conseguir aplicar com segurança, informar e seguir. Briefing não vira refém de updater manco.

## Changelog

Histórico completo de versão vive em `CHANGELOG.md`.

Versão atual deste core:

- `4.16.4`

---

*Prumo Core v4.16.4 — https://github.com/tharso/prumo*
