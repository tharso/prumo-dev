# Prumo Core — Motor do sistema

> **prumo_version: 4.19.0**
>
> Este arquivo é o núcleo estável do Prumo.
> Ele define regras, guardrails e a localização dos módulos canônicos.
> Procedimento detalhado não mora mais aqui.
>
> Repositório: https://github.com/tharso/prumo
> Arquivo remoto: https://raw.githubusercontent.com/tharso/prumo/main/skills/prumo/references/prumo-core.md

---

## Estrutura do workspace

```text
[Workspace]/
├── CLAUDE.md              ← ponteiro → Prumo/AGENT.md
├── AGENT.md               ← ponteiro → Prumo/AGENT.md
├── AGENTS.md              ← ponteiro → Prumo/AGENT.md
├── Prumo/
│   ├── AGENT.md           ← fonte canônica (navegação, fallback, regras)
│   ├── PAUTA.md
│   ├── INBOX.md
│   ├── REGISTRO.md
│   ├── IDEIAS.md
│   ├── Agente/
│   │   ├── INDEX.md
│   │   ├── PERFIL.md
│   │   └── PESSOAS.md
│   ├── Referencias/
│   ├── Inbox4Mobile/
│   └── skills/            ← cópia das skills do repo
└── .prumo/
    ├── state/
    ├── system/
    │   └── PRUMO-CORE.md  ← este arquivo
    └── logs/
```

Arquivos de estado esperados em `.prumo/state/`:

- `briefing-state.json`
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
| `/sanitize` | Sanitizar estado operacional |
| `/higiene` | Higiene assistida do `Prumo/Agente/PERFIL.md` |
| `/start` | Captura inicial e onboarding rápido |
| `/prumo` | Alias legado de setup |

No Cowork, os comandos canônicos aparecem sem prefixo do plugin.
Alias legado ainda pode existir por compatibilidade, mas documentação nova deve usar o formato curto.

Se o runtime CLI não estiver disponível, usar a cadeia de fallback definida em `Prumo/AGENT.md` (skill direto).

## Módulos canônicos

Quando um comando específico for executado, o agente deve ler o módulo correspondente antes de agir.

| Assunto | Módulo canônico |
|---|---|
| Briefing | `Prumo/skills/prumo/references/modules/briefing-procedure.md` |
| Inbox | `Prumo/skills/prumo/references/modules/inbox-processing.md` |
| Revisão semanal | `Prumo/skills/prumo/references/modules/weekly-review.md` |
| Update de versão | `Prumo/skills/prumo/references/modules/version-update.md` |
| Multiagente | `Prumo/skills/prumo/references/modules/multiagent.md` |
| Sanitização | `Prumo/skills/prumo/references/modules/sanitization.md` |
| Higiene do perfil | `Prumo/skills/prumo/references/modules/claude-hygiene.md` |
| Runtime do Cowork | `Prumo/skills/prumo/references/modules/cowork-runtime-maintenance.md` |
| Bridge do runtime no Cowork | `Prumo/skills/prumo/references/modules/cowork-runtime-bridge.md` |
| Contrato de interface | `Prumo/skills/prumo/references/modules/interaction-format.md` |
| Governança de arquivos | `Prumo/skills/prumo/references/modules/runtime-file-governance.md` |
| Política de leitura | `Prumo/skills/prumo/references/modules/load-policy.md` |
| Runtime paths | `Prumo/skills/prumo/references/modules/runtime-paths.md` |
| Feedback do produto | `Prumo/skills/prumo/references/feedback-loop.md` |

Se o runtime não expuser o repositório local `Prumo/skills/`, ele deve usar a referência equivalente do bundle instalado. O que não pode é improvisar uma terceira versão do procedimento.

## Política de leitura

1. Sempre ler `Prumo/AGENT.md`, `.prumo/system/PRUMO-CORE.md`, `Prumo/PAUTA.md` e `Prumo/INBOX.md`.
2. Para comando específico, ler também o módulo canônico correspondente.
3. Preferir leitura leve quando disponível:
   - `Prumo/Inbox4Mobile/_preview-index.json`
   - `Prumo/Inbox4Mobile/inbox-preview.html`
   - Gmail MCP / Calendar MCP direto
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

Tom vem de `Prumo/Agente/PERFIL.md`, mas item parado continua merecendo cobrança. O que muda é a faca, não o corte.

### 5. Ideias não são ações

Sem próxima ação concreta, vai para `Prumo/IDEIAS.md`, não para `Prumo/PAUTA.md`.

### 6. Registro antes do sumiço

Se um item vai ser movido, arquivado ou deletado, isso precisa passar por `Prumo/REGISTRO.md`.

### 7. Revisão semanal é poda

Na revisão semanal, mostrar tudo, inclusive agendados com cobrança futura. Supressão temporal é só para briefing diário.

### 8. Se sumiu, recomece

Gap grande de uso pede brain dump fresco, não arqueologia emocional.

### 9. Proatividade obrigatória

O Prumo deve mirar ação concreta, não listinha passiva. Nível 3 ou 4 sempre que houver material para isso.

### 10. Multiagente exige cooperação explícita

Sem lock ativo, escrita simultânea em estado compartilhado vira corrida. Dois agentes tocando o mesmo arquivo sem coordenação é bagunça com log bonito.

### 11. Atualização segura só toca o motor

Update pode mexer em `.prumo/system/PRUMO-CORE.md` e backup. O resto é área do usuário. Mão fora.

### 12. Briefing é progressivo

Primeiro panorama, depois proposta, detalhe só sob demanda.

### 13. Feedback do produto é comportamento do sistema

Se o usuário der feedback, bug ou sugestão sobre o Prumo em si, capturar isso e usar `Prumo/skills/prumo/references/feedback-loop.md` como procedimento canônico.

### 14. Fluxo não perde contagem

Quando a resposta fizer parte do mesmo fluxo, a numeração deve continuar de onde estava. Resetar a lista a cada bloco é jeito elegante de parecer desorientado.

### 15. Escolha fácil vale ouro

Sempre que houver mais de um caminho razoável, oferecer alternativas curtas e respondíveis (`a)`, `b)`, `c)`) em vez de empurrar o usuário para resposta aberta sem necessidade.

## Guardrails

`ASSERT: Usar Gmail MCP e Calendar MCP como fonte primária de email e calendário.`

`ASSERT: Se existir Prumo/Inbox4Mobile/_preview-index.json, linkar inbox-preview.html antes de abrir qualquer arquivo bruto.`

`ASSERT: Antes de deletar item de inbox, confirmar com o usuário o plano único de commit.`

`ASSERT: Registrar no Prumo/REGISTRO.md antes de remover o original do inbox.`

`ASSERT: last_briefing_at deve ser persistido antes da primeira resposta do briefing.`

`ASSERT: Na primeira resposta do briefing, é proibido abrir arquivo bruto de Prumo/Inbox4Mobile/*.`

`ASSERT: interrupted_at e resume_point só existem quando o usuário acionou escape hatch.`

`ASSERT: No update, a allowlist de escrita é apenas .prumo/system/PRUMO-CORE.md e .prumo/backup/PRUMO-CORE.md.*`

`ASSERT: Antes do panorama do briefing, o sistema deve tentar preflight de versão e avisar quando detectar versão nova.`

`ASSERT: Se Prumo/VERSION local for maior que prumo_version do workspace, o briefing deve acusar core defasado antes de seguir.`

`ASSERT: Arquivo frio só pode ser movido para archive se houver entrada correspondente em .prumo/state/archive/ARCHIVE-INDEX.*`

`ASSERT: Prumo/Agente/PERFIL.md nunca entra em autosanitização; higiene só acontece com confirmação explícita do usuário.`

`ASSERT: Pendência viva, registro resolvido e histórico não devem disputar espaço em Prumo/Agente/PERFIL.md como se fossem a mesma espécie de informação.`

## Rituais e procedimentos

### Briefing diário

Ler e seguir:

- `Prumo/skills/prumo/references/modules/briefing-procedure.md`

Esse módulo cobre:

- `last_briefing_at`, `interrupted_at`, `resume_point`
- antes da primeira resposta do briefing, persistir `last_briefing_at`
- capturar em memória o `last_briefing_at` anterior para usar como janela da sessão
- Gmail MCP e Calendar MCP como fonte primária
- janela temporal via `last_briefing_at` ou fallback 24h
- `Bloco 1`, `Bloco 2`, `--detalhe`
- regra de 24h quando não houver estado

### Inbox processing

Ler e seguir:

- `Prumo/skills/prumo/references/modules/inbox-processing.md`

Esse módulo cobre:

- `Responder`, `Ver`, `Sem ação`
- `P1/P2/P3`
- `_preview-index.json`
- `inbox-preview.html`
- `_processed.json`
- `| cobrar: DD/MM`

### Revisão semanal

Ler e seguir:

- `Prumo/skills/prumo/references/modules/weekly-review.md`

### Update de versão

Ler e seguir:

- `Prumo/skills/prumo/references/modules/version-update.md`

Esse módulo é a fonte canônica para:

- transporte seguro de aplicação
- Nunca usar WebFetch para aplicar update
- fallback que não bloqueia o briefing quando o runtime não consegue baixar o core bruto com segurança
- aviso como "nova versão do motor" quando não houver changelog local seguro

### Multiagente

Ler e seguir:

- `Prumo/skills/prumo/references/modules/multiagent.md`

### Sanitização

Ler e seguir:

- `Prumo/skills/prumo/references/modules/sanitization.md`

### Higiene do perfil

Ler e seguir:

- `Prumo/skills/prumo/references/modules/claude-hygiene.md`

### Runtime paths

Ler e seguir:

- `Prumo/skills/prumo/references/modules/runtime-paths.md`

## Durante o dia

O usuário pode fazer dump, check-in, pedir cobrança futura ou rodar sanitização. A regra continua a mesma: ler o módulo certo, atualizar o estado certo e não fingir que lembrou tudo de cabeça.

## Observações de runtime

- Com shell: preferir scripts oficiais (`safe_core_update.sh`, `prumo_briefing_state.py`, `prumo_auto_sanitize.py`, `generate_inbox_preview.py`).
- Sem shell: manter paridade de curadoria e transparência sobre limitações.
- Se o runtime só detectar versão nova, mas não conseguir aplicar com segurança, informar e seguir. Briefing não vira refém de updater manco.

## Changelog

Histórico completo de versão vive em `CHANGELOG.md`.

Versão atual deste core:

- `4.19.0`

---

*Prumo Core v4.19.0 — https://github.com/tharso/prumo*
