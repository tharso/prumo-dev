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
2. Tente fonte remota:
   - versão: `https://raw.githubusercontent.com/tharso/prumo/main/VERSION`
   - core: `https://raw.githubusercontent.com/tharso/prumo/main/cowork-plugin/skills/prumo/references/prumo-core.md`
3. Validar integridade da fonte remota antes de usar:
   - tratar como inválida se o core remoto estiver truncado (ex.: sem `## Changelog do Core` ou sem rodapé `Prumo Core v...`);
   - em fonte inválida, cair para fallback local.
4. Se a fonte remota falhar (404/auth/rede) **ou for inválida/incompleta**, tente fonte local (se existir no workspace):
   - versão: `Prumo/VERSION`
   - core (layout atual): `Prumo/cowork-plugin/skills/prumo/references/prumo-core.md`
   - core (layout legado): `Prumo/skills/prumo/references/prumo-core.md`
5. Se nenhuma fonte estiver acessível, informe: "Não consegui verificar atualização do Prumo agora (falha de acesso à fonte de versão)." e prossiga. Nunca afirmar "já está atualizado" sem fonte válida.
6. Se a versão encontrada for maior, informe: "Há uma atualização do Prumo (v[local] → v[remota]). A atualização pode tocar SOMENTE `PRUMO-CORE.md`. `CLAUDE.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`, `AGENTS.md` e demais arquivos pessoais não podem ser alterados. Quer atualizar?"
7. Se aceitar:
   - Fazer backup de `PRUMO-CORE.md` em `_backup/PRUMO-CORE.md.YYYY-MM-DD-HHMMSS` (se a pasta `_backup/` não existir, criar).
   - Substituir apenas `PRUMO-CORE.md` usando o core da fonte válida.
   - Regra absoluta: se qualquer outra escrita for necessária, abortar a atualização e pedir confirmação explícita do usuário.
8. Se recusar ou se já estiver atualizado: prossiga.

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
2. **Google dual via Gemini CLI (prioridade quando disponível)**:
   - Se existir `scripts/prumo_google_dual_snapshot.sh`, executar esse script.
   - Usar a saída do script como fonte principal para agenda (`AGENDA_HOJE` + `AGENDA_AMANHA`) e curadoria de emails (`TRIAGEM_RESPONDER`, `TRIAGEM_VER`, `TRIAGEM_SEM_ACAO`) das contas `pessoal` e `trabalho`.
   - Respeitar a janela "desde o último briefing" informada no próprio script.
   - Se uma conta falhar (auth/MCP), sinalizar no briefing e manter a outra conta.
3. **Fallback sem shell (paridade obrigatória de curadoria)**:
   - Se o script dual não existir ou não puder executar no runtime, usar integração nativa de Gmail/Calendar.
   - Definir janela de análise de email:
     - Se existir `_state/briefing-state.json` com `last_briefing_at`, usar esse timestamp.
     - Senão, usar fallback de 24h.
   - Buscar emails recebidos na janela e classificar com o mesmo padrão:
     - `Responder` (exige resposta ativa)
     - `Ver` (exige leitura/checagem, sem resposta imediata)
     - `Sem ação` (baixo valor imediato)
   - Atribuir prioridade `P1/P2/P3` e motivo objetivo em cada item.
4. **Google Calendar fallback** (se configurado): listar eventos de hoje e amanhã.

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

Se a PAUTA estiver vazia: não fazer o briefing padrão. Pedir um brain dump.

## Passo 7: Documentar

Atualizar PAUTA.md se algo mudou. Registrar itens processados no REGISTRO.md.
Se houve validação de handover, atualizar status no `_state/HANDOVER.md`.
Se existir `_state/HANDOVER.summary.md`, atualizar via sanitização quando houver grande volume de handovers fechados.
Se houve fallback sem deleção física, manter `Inbox4Mobile/_processed.json` atualizado para evitar reapresentação de itens já processados.

### Atualizar estado do briefing (obrigatório, sem exceção)

Esta etapa é **bloqueante**: o briefing só está concluído quando `_state/briefing-state.json` refletir o estado correto. Não depende de nenhum script externo.

**Se o briefing foi concluído normalmente:**

Escrever `_state/briefing-state.json` com exatamente este conteúdo (substituindo o timestamp pelo horário local real no fuso do usuário):

```json
{
  "last_briefing_at": "YYYY-MM-DDTHH:MM:SS-03:00"
}
```

O arquivo não deve conter `interrupted_at` nem `resume_point` (limpar se existirem).

Como obter o timestamp: executar `date +%Y-%m-%dT%H:%M:%S%:z` via shell, ou usar a hora do sistema no fuso configurado no `CLAUDE.md`.

**Se o briefing foi interrompido (escape hatch):**

Manter `last_briefing_at` como está e adicionar estado de retomada:

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

Após escrever o arquivo, ler `_state/briefing-state.json` e validar de forma condicional:

- briefing concluído: confirmar que `last_briefing_at` contém a data do dia local atual e que `interrupted_at`/`resume_point` não existem;
- briefing interrompido: confirmar que `interrupted_at` contém a data do dia local atual, que `resume_point` foi gravado, e que `last_briefing_at` foi preservado (sem forçar carimbo de conclusão).

Se a validação correspondente falhar, repetir a escrita correta para esse caso.

---

**Tom:** Seguir rigorosamente o tom definido no CLAUDE.md do usuário. Se for "direto", cobrar sem cerimônia. Se for "gentil", lembrar sem pressionar.

**Links:** Sempre usar `[Descrição](computer:///caminho)` ao referenciar arquivos. Nunca expor caminhos crus.
