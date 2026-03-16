---
name: briefing
description: >
  Morning briefing do Prumo. Executa a rotina completa: lê configuração pessoal,
  verifica pauta, processa inbox (todos os canais), checa calendário e emails,
  e apresenta o briefing do dia. Use com /prumo:briefing (alias legado: /briefing) ou quando o usuário disser
  "bom dia", "briefing", "começar o dia".
---

# Briefing do Prumo

Você está executando o morning briefing do sistema Prumo. Esta é a rotina mais importante do sistema. Siga os passos abaixo **na ordem**, sem pular nenhum.

## Passo 1: Ler configuração

1. Leia o arquivo `CLAUDE.md` na pasta workspace do usuário. Ele contém: nome, áreas de vida, tom de comunicação, integrações configuradas, lembretes recorrentes.
2. Leia o arquivo `PRUMO-CORE.md` na mesma pasta. Ele contém as regras do sistema.
3. Extraia o fuso do usuário do `CLAUDE.md` (default: `America/Sao_Paulo`) e use esse fuso para qualquer referência de data relativa (`hoje`, `amanhã`, dia da semana).
4. Determine a data local por fonte verificável (ordem de preferência): ferramenta de tempo com timezone, relógio do sistema com TZ explícito, APIs de calendário no mesmo fuso.
5. Se não houver fonte confiável, NÃO anunciar dia/data textual no cabeçalho do briefing.

Se algum desses arquivos não existir, informe o usuário que o Prumo não está configurado e sugira rodar o setup.

## Passo 2: Verificar atualização

1. Leia o campo `prumo_version` no topo do `PRUMO-CORE.md` local.
2. Tente fonte remota **apenas para comparar versão**:
   - versão: `https://raw.githubusercontent.com/tharso/prumo/main/VERSION`
3. Nunca use WebFetch, leitor inteligente, preview remoto ou qualquer resposta resumida/interpretada como fonte para reescrever `PRUMO-CORE.md`. Isso conta como fonte inválida para update, mesmo que o texto "pareça certo".
4. Descubra se existe **transporte seguro de aplicação**:
   - fonte local de manutenção no workspace:
     - versão: `Prumo/VERSION`
     - core (layout atual): `Prumo/cowork-plugin/skills/prumo/references/prumo-core.md`
     - core (layout legado): `Prumo/skills/prumo/references/prumo-core.md`
   - updater via shell:
     - `scripts/safe_core_update.sh`
     - `Prumo/cowork-plugin/scripts/safe_core_update.sh`
     - `Prumo/scripts/safe_core_update.sh`
5. Se nenhuma fonte de versão estiver acessível, informe: "Não consegui verificar atualização do Prumo agora (falha de acesso à fonte de versão)." e prossiga. Nunca afirmar "já está atualizado" sem fonte válida.
6. Se a versão encontrada for maior **e houver transporte seguro de aplicação**, informe: "Há uma atualização do Prumo (v[local] → v[remota]). A atualização pode tocar SOMENTE `PRUMO-CORE.md`. `CLAUDE.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`, `AGENTS.md` e demais arquivos pessoais não podem ser alterados. Quer atualizar?"
   - Nunca buscar changelog remoto via WebFetch só para enriquecer esse aviso. Se não houver changelog local seguro, anunciar a nova versão sem changelog detalhado.
7. Se a versão encontrada for maior **e não houver transporte seguro de aplicação**, informe em 1 bloco objetivo:
   - existe atualização disponível;
   - este runtime consegue comparar versões, mas não consegue baixar o core bruto com segurança;
   - a correção exige atualizar/reinstalar o plugin ou usar um ambiente com shell/repo local;
   - não bloquear o briefing por causa disso.
8. Se aceitar e houver fonte local válida:
   - Fazer backup de `PRUMO-CORE.md` em `_backup/PRUMO-CORE.md.YYYY-MM-DD-HHMMSS` (se a pasta `_backup/` não existir, criar).
   - Substituir apenas `PRUMO-CORE.md` usando o arquivo local bruto da fonte válida.
9. Se aceitar e houver updater via shell:
   - executar o updater seguro (`safe_core_update.sh`) apontando para o workspace atual;
   - reler `PRUMO-CORE.md` e confirmar que `prumo_version` mudou para a versão esperada.
10. Regra absoluta: se qualquer outra escrita for necessária, abortar a atualização e pedir confirmação explícita do usuário.
11. Se recusar ou se já estiver atualizado: prossiga.

## Passo 3: Estado atual

1. Leia `PAUTA.md` — este é o arquivo mais importante.
2. Leia `INBOX.md` — se tiver itens, serão processados no passo 5.
3. Verifique handovers em modo leve:
   - se existir `_state/HANDOVER.summary.md`, use como fonte principal;
   - se não existir ou estiver desatualizado, leia `_state/HANDOVER.md`;
   - identifique itens em `PENDING_VALIDATION` ou `REJECTED`.
4. Se existir `_state/auto-sanitize-state.json`, leia para telemetria de manutenção (última execução/último apply).
5. Se existir `_state/auto-sanitize-history.json`, use amostra leve quando precisar explicar thresholds adaptativos.
6. Se existir `_state/briefing-state.json`, trate estado de retomada:
   - se houver `interrupted_at` + `resume_point` no mesmo dia local, pergunte: `a) retomar` ou `b) recomeçar`;
   - se `interrupted_at` for de dia anterior, expire silenciosamente (limpe `interrupted_at`/`resume_point`) e siga sem cobrar briefing antigo.
   - antes de qualquer escrita nova, capture em memória o `last_briefing_at` anterior para usar como janela desta sessão.
7. Monte supressão temporal dos agendados:
   - parsear `| cobrar: DD/MM` (ou `DD/MM/AAAA`) nos itens de `Agendado`;
   - se `cobrar` estiver no futuro, item fica silenciado no briefing diário;
   - se `cobrar` for hoje/passado, item fica elegível para proposta do dia.

## Passo 4: Canais de entrada

Verificar TODOS os canais, sem pular nenhum:

0. **Autosanitização preventiva (quando shell disponível)**:
   - Rodar `if [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace . --apply; elif [ -f Prumo/cowork-plugin/scripts/prumo_auto_sanitize.py ]; then python3 Prumo/cowork-plugin/scripts/prumo_auto_sanitize.py --workspace . --apply; else python3 Prumo/scripts/prumo_auto_sanitize.py --workspace . --apply; fi`.
   - Se falhar, reportar em 1 linha e seguir briefing (não bloquear rotina).

1. **Pasta `Inbox4Mobile/`**: Listar TODOS os arquivos e iniciar por triagem leve (não abrir bruto de todos por padrão).
   - Se existir `Inbox4Mobile/_processed.json`, usar como filtro para não reapresentar como "novos" os itens já processados em sessão anterior sem deleção física.
   - Rodar em **2 estágios obrigatórios**:
     - Estágio A (triagem leve): regenerar SEMPRE `Inbox4Mobile/inbox-preview.html` + `Inbox4Mobile/_preview-index.json` no início do briefing (quando shell disponível).
     - com shell: `if [ -f scripts/generate_inbox_preview.py ]; then python3 scripts/generate_inbox_preview.py --output Inbox4Mobile/inbox-preview.html --index-output Inbox4Mobile/_preview-index.json; elif [ -f Prumo/cowork-plugin/scripts/generate_inbox_preview.py ]; then python3 Prumo/cowork-plugin/scripts/generate_inbox_preview.py --output Inbox4Mobile/inbox-preview.html --index-output Inbox4Mobile/_preview-index.json; else python3 Prumo/scripts/generate_inbox_preview.py --output Inbox4Mobile/inbox-preview.html --index-output Inbox4Mobile/_preview-index.json; fi`.
     - sem shell: gerar HTML equivalente inline + índice textual equivalente (tipo, tamanho, data, link).
     - Regra bloqueante de adoção: se `Inbox4Mobile/_preview-index.json` existir, o agente DEVE linkar `Inbox4Mobile/inbox-preview.html` no briefing como primeiro passo da triagem.
     - Não abrir arquivos brutos individuais antes desse link, exceto em caso de falha objetiva de geração/leitura do preview.
     - Estágio B (aprofundamento): abrir conteúdo bruto completo apenas para itens `P1`, ambíguos, risco legal/financeiro/documental, ou solicitação explícita do usuário.
   - Se a geração falhar e existir preview anterior, ainda linkar o preview e explicitar que pode estar defasado.
   - Se a geração falhar sem preview utilizável, seguir com lista numerada no chat (fallback universal), mantendo a regra de aprofundamento seletivo e explicitando a falha de preview ao usuário.
   - No Bloco 1 (panorama), mostrar apenas o link do preview e a contagem de itens (sem abrir itens individuais).
2. **Snapshots no Google Drive via Apps Script (prioridade quando disponíveis)**:
   - Buscar via MCP do Google Drive os arquivos `Prumo/snapshots/email-snapshot.json` das contas conectadas.
   - Tratar cada snapshot como fonte por conta (`pessoal`/`trabalho`) para agenda e emails crus.
   - Validar `generated_at` de cada arquivo:
     - se estiver com mais de 30 min, usar mesmo assim, mas avisar explicitamente no briefing que os dados estão defasados e dizer de quantos minutos;
     - se o arquivo estiver ausente, ilegível ou inválido, seguir para o fallback sem quebrar o briefing.
   - Respeitar o `since` gravado no próprio snapshot quando ele existir. Não recalcular essa janela por cima.
   - Se o JSON trouxer `emails_error` ou `calendar_error`, preservar os dados parciais disponíveis e expor o erro em 1 linha objetiva.
   - A curadoria continua no Prumo, não no Apps Script:
     - classificar emails em `Responder`, `Ver` e `Sem ação`;
     - atribuir prioridade `P1/P2/P3` com motivo objetivo;
     - consolidar agenda por conta no panorama.
   - Timebox de leitura: 45 segundos no total. Se estourar, seguir briefing sem email/calendar e avisar.
3. **Google dual via Gemini CLI (fallback com shell)**:
   - Se os snapshots não estiverem disponíveis ou válidos e existir `scripts/prumo_google_dual_snapshot.sh`, executar esse script.
   - Usar a saída do script como fonte principal para agenda (`AGENDA_HOJE` + `AGENDA_AMANHA`) e curadoria de emails (`TRIAGEM_RESPONDER`, `TRIAGEM_VER`, `TRIAGEM_SEM_ACAO`) das contas `pessoal` e `trabalho`.
   - Respeitar a janela "desde o último briefing" informada no próprio script.
   - Se uma conta falhar (auth/MCP), sinalizar no briefing e manter a outra conta.
4. **Fallback sem shell (paridade obrigatória de curadoria)**:
   - Se o script dual não existir ou não puder executar no runtime, usar integração nativa de Gmail/Calendar.
   - Definir janela de análise de email:
     - Se existir `_state/briefing-state.json` com `last_briefing_at`, usar esse timestamp.
     - Senão, usar fallback de 24h.
   - Buscar emails recebidos na janela e classificar com o mesmo padrão:
     - `Responder` (exige resposta ativa)
     - `Ver` (exige leitura/checagem, sem resposta imediata)
     - `Sem ação` (baixo valor imediato)
   - Atribuir prioridade `P1/P2/P3` e motivo objetivo em cada item.
5. **Google Calendar fallback** (se configurado): listar eventos de hoje e amanhã.

## Passo 5: Processar inbox

Se houver itens novos (de qualquer canal):
- Numerar cada item
- Sugerir categoria e próxima ação com `Responder`/`Ver`/`Sem ação` e `P1`/`P2`/`P3`
- Perguntar ao usuário se concorda ou quer ajustar
- Montar plano único de commit com todas as operações pendentes
- Pedir confirmação explícita antes de executar: "Vou executar estas N operações. Confirma?"
- Executar em lote:
  - mover para PAUTA.md ou README da área
  - adicionar `(desde DD/MM)` em cada item
  - se item for agendado futuro, perguntar data de cobrança e registrar `| cobrar: DD/MM`
  - renomear arquivos com nomes descritivos
  - registrar no REGISTRO.md
  - deletar original do inbox com ação real de filesystem
- Tratar permissão de deleção por runtime:
  - quando necessário, solicitar proativamente permissão (ex.: `allow_cowork_file_delete`) antes de deletar
  - se falhar por permissão, solicitar e tentar novamente
  - se continuar falhando, registrar `DELECAO_FALHOU` no REGISTRO.md (com motivo) e marcar item em `Inbox4Mobile/_processed.json`
- Verificar pós-commit: listar `Inbox4Mobile/` e confirmar que itens processados não ficaram para trás
- Reportar fechamento: quantos processados, quantos deletados, quantos falharam e por quê

## Passo 6: Montar o briefing

Montar o briefing em blocos progressivos (não despejar tudo de uma vez):

1. **Bloco 1 — Panorama (automático, sem interação)**
   - abertura com data correta (formato absoluto no fuso do usuário);
   - agenda do dia (consolidada por conta quando aplicável);
   - link para `Inbox4Mobile/inbox-preview.html` quando `_preview-index.json` existir;
   - contagem silenciosa de agendados da semana (incluindo os suprimidos por `| cobrar: ...`, sem listar individualmente);
   - pendências de handover (`PENDING_VALIDATION`/`REJECTED`) em 1 linha objetiva.
2. **Bloco 2 — Proposta do dia (uma única interação obrigatória)**
   - propor foco com base em: deadlines de hoje, blockers, tempo disponível na agenda e itens com cobrança elegível hoje;
   - apresentar exatamente:
     - `a) Aceitar e seguir`
     - `b) Ajustar (me diz o que muda)`
     - `c) Ver lista completa`
     - `d) Tá bom por hoje`
3. **Opção c (contexto completo sob demanda)**
   - mostrar andamento, atrasados/parados (`desde DD/MM`), agendados da semana e cobranças elegíveis;
   - após mostrar, voltar para a mesma decisão do Bloco 2 sem resetar briefing.
4. **Opção d (escape hatch)**
   - registrar `interrupted_at` e `resume_point` em `_state/briefing-state.json`;
   - encerrar briefing sem cobrança adicional.
5. **Escape por linguagem natural**
   - se usuário disser "tá bom por hoje", "escape", "depois" ou equivalente em qualquer etapa, aplicar o mesmo fluxo de escape.
6. **Modo detalhado direto**
   - se usuário chamar `/prumo:briefing --detalhe`, abrir contexto completo sem pular Bloco 1.
7. **Guardrail da primeira interação**
   - na primeira resposta do briefing, é proibido abrir `Inbox4Mobile/*` individualmente;
   - primeiro vem panorama + proposta; arquivo bruto só após `c`/`--detalhe` ou solicitação explícita.
8. **Persistência de início do briefing (obrigatória)**
   - antes de enviar a primeira resposta com Bloco 1 + Bloco 2, persistir o início do briefing do dia em `_state/briefing-state.json`;
   - se houver shell, preferir:
     - `python3 scripts/prumo_briefing_state.py --workspace . --timezone <TZ> --mode start`
     - `python3 Prumo/cowork-plugin/scripts/prumo_briefing_state.py --workspace . --timezone <TZ> --mode start`
     - `python3 Prumo/scripts/prumo_briefing_state.py --workspace . --timezone <TZ> --mode start`
   - sem shell, escrever manualmente `last_briefing_at` com timestamp ISO local do momento e limpar `interrupted_at`/`resume_point`;
   - validar antes de responder: o arquivo precisa refletir a data local de hoje.

Se a PAUTA estiver vazia: não fazer o briefing padrão. Pedir um brain dump.

## Passo 7: Documentar

Atualizar PAUTA.md se algo mudou. Registrar itens processados no REGISTRO.md.
Se houve validação de handover, atualizar status no `_state/HANDOVER.md`.
Se existir `_state/HANDOVER.summary.md`, atualizar via sanitização quando houver grande volume de handovers fechados.
Se houve fallback sem deleção física, manter `Inbox4Mobile/_processed.json` atualizado para evitar reapresentação de itens já processados.

### Atualizar estado do briefing (obrigatório, sem exceção)

Esta etapa é **bloqueante**. O briefing do dia só está oficialmente aberto quando `_state/briefing-state.json` já refletir o início da sessão antes da primeira resposta. Não depende de script externo, mas quando houver shell deve preferir `prumo_briefing_state.py`.

**No início do briefing (antes da primeira resposta):**

- persistir `last_briefing_at` com o timestamp ISO local atual;
- limpar `interrupted_at` e `resume_point`;
- usar o valor anterior de `last_briefing_at` (capturado em memória no Passo 3) como janela desta sessão. Nunca recalcular a janela a partir do valor recém-gravado no mesmo briefing.

**Se o briefing foi concluído normalmente depois disso:**

- apenas confirmar que `interrupted_at`/`resume_point` continuam ausentes;
- se o início não tiver sido persistido por algum motivo, gravar `last_briefing_at` nesse momento como fallback.

**Se o briefing foi interrompido (escape hatch):**

Manter `last_briefing_at` já gravado no início da sessão e adicionar estado de retomada:

```json
{
  "last_briefing_at": "[valor existente, não alterar]",
  "interrupted_at": "YYYY-MM-DDTHH:MM:SS-03:00",
  "resume_point": "[etapa onde parou, ex: bloco2_proposta]"
}
```

**Expiração de estado interrompido:**

No início de novo dia, se `interrupted_at` for de dia anterior, limpar `interrupted_at` e `resume_point` silenciosamente (sem cobrar briefing antigo).

**Validação pós-escrita:**

Após cada escrita, ler `_state/briefing-state.json` e validar de forma condicional:

- briefing iniciado/concluído: confirmar que `last_briefing_at` contém a data do dia local atual e que `interrupted_at`/`resume_point` não existem;
- briefing interrompido: confirmar que `interrupted_at` contém a data do dia local atual, que `resume_point` foi gravado, e que `last_briefing_at` continua apontando para o início da sessão atual.

Se a validação correspondente falhar, repetir a escrita correta para esse caso.

---

**Tom:** Seguir rigorosamente o tom definido no CLAUDE.md do usuário. Se for "direto", cobrar sem cerimônia. Se for "gentil", lembrar sem pressionar.

**Links:** Sempre usar `[Descrição](computer:///caminho)` ao referenciar arquivos. Nunca expor caminhos crus.
