---
name: fim
description: >
  Encerramento formal de sessão do Prumo. Quando o usuário diz "/fim", "terminar
  por hoje", "encerrar a sessão", "fechar o dia", "acabei", a skill documenta os
  deltas duráveis da sessão nos canais existentes (sem perder ideia ou status
  entre sessões), gera o diário do dia em Prumo/Diario/ (projeção confirmada
  dos fatos gravados — nunca reconstrução de memória), roda a faxina
  automática, mostra um resumo, e — se detectar acúmulo — PROPÕE (não executa)
  UMA recomendação de limpeza em linguagem comum. É o bookend simétrico do briefing: o briefing
  abre, o fim fecha. NÃO é briefing (não lê email/calendário, não monta a
  pauta do dia).
---

# Fim

Encerramento de sessão. Porta única que resolve dois problemas: (a) ideias e
status discutidos na sessão **evaporam** entre sessões; (b) os comandos de
limpeza (`faxina`, `higiene`, `sanitize`) ficam **esquecidos** e o workspace
acumula lixo. O `/fim` é o bookend do `/briefing` — um abre o dia, o outro fecha.

## Contrato conservador (anti-evaporação honesta)

Documentar a sessão **não** é reconstruir o que foi dito de memória. Contexto é
volátil — compactação destrói memória textual (ver CLAUDE.md). Então o `/fim`
segue um procedimento **verificável**, não fé na própria honestidade:

1. **Listar candidatos** a delta durável — decisões tomadas, itens criados ou
   mudados — **com a origem visível** na sessão (não do nada).
2. **Confirmar** um resumo curto com o usuário antes de gravar.
3. **Gravar só o confirmado**, nos **canais que já existem**:
   - ideia sem próxima ação → `IDEIAS.md`
   - tarefa nova / mudança de status → `PAUTA.md`
   - fato / decisão / trabalho concluído → `REGISTRO.md`
4. **Sob compactação:** se a sessão foi compactada, o default é **não registrar
   fato anterior ao trecho visível** — declarar a lacuna ao usuário ("não
   consigo garantir o começo da sessão"). A ressalva é cinto de segurança, não
   licença pra dirigir no escuro.

**Proibido (mantém a #68, emendada pela decisão 2026-07-02/#141):** reconstruir
sessão no escuro; redigir narrativa **de memória** (sem fato gravado que a
sustente); gerar artefato de coordenação entre agentes (`HANDOVER`,
`PENDING_VALIDATION`, doc de validação) em qualquer lugar — e qualquer artefato
narrativo em `skills/`, `runtime/` ou `.prumo/state/`. O `/fim` grava **fatos em
canais existentes** e uma única exceção contratada: o **diário do dia** (passo
2) — projeção confirmada dos fatos gravados, em `Prumo/Diario/`, nunca
reconstrução.

## O fluxo

```
1. DOCUMENTAR → deltas visíveis e confirmados → IDEIAS / PAUTA / REGISTRO
2. DIÁRIO     → projeção dos fatos do dia → confirmação do texto completo → Prumo/Diario/AAAA-MM-DD.md
3. FAXINA     → roda a rotina automática (já é no-confirm)
4. RESUMO     → o que registrou + o diário + o que a faxina arrumou
5. DETECTAR   → `prumo fim --workspace <ws> --format json` aponta acúmulo; PROPOR a recomendação (conteúdo > técnica)
```

### Passo 2 — Diário do dia

Depois de gravar os deltas, gerar o relato do dia em `Prumo/Diario/AAAA-MM-DD.md`
(data local do usuário). O diário é **projeção dos fatos confirmados — não
redação livre**:

1. **Fonte exclusiva:** fatos gravados/confirmados — `REGISTRO.md` do dia,
   movimentos da `PAUTA.md` (concluídos), deltas que o passo 1 acabou de
   confirmar. Cada linha rastreável a um fato gravado. Prosa conectiva mínima;
   **inferência nova, não** (nada de "parece que o dia foi produtivo").
2. **Conteúdo enxuto:** o que foi concluído, o que foi decidido, o que entrou
   de novo, o que travou, o que ficou pra amanhã. Sem agenda/emails (decisão
   do dono, 2026-07-02 — reavaliar com o uso).
3. **Confirmação do texto completo:** exibir o diário inteiro e só gravar após
   OK do usuário. Confirmar bullets e gerar prosa nova por fora é reconstrução
   disfarçada — vedado.
4. **Sob compactação:** herda o contrato conservador do passo 1 — só o
   visível/confirmado; declarar a lacuna **no próprio diário** ("sessão
   compactada; começo do dia não coberto").
5. **Sem retro-geração:** se o `/fim` não rodou num dia, não há diário daquele
   dia. Nunca inventar dias passados.
6. **Segundo `/fim` no mesmo dia:** se o arquivo já existe, **anexar** uma
   seção nova (`## Sessão HH:MM`) só com os fatos novos, com a mesma
   confirmação do texto completo do trecho anexado. Nunca sobrescrever nem
   regenerar texto já confirmado; fato já registrado no diário do dia não se
   repete.
7. **A pasta nasce aqui:** `Prumo/Diario/` é criada pelo primeiro `/fim` que
   gerar diário — o setup não a pré-cria (regra 16 do core). Se o usuário
   recusar o diário da vez, tudo bem: os fatos continuam nos canais do passo
   1; o diário é conveniência de leitura, não requisito.

### Passo 3 — Faxina (automático)

Rodar a `faxina` (rotaciona REGISTRO, migra pauta concluída, atualiza índices,
limpa processados antigos). É a limpeza que **não exige julgamento** — corre
sozinha, como já corre no início do briefing.

### Passo 5 — Detecção de acúmulo (propõe, não executa)

Rodar `prumo fim --workspace <ws> --format json` (read-only). Ele computa sinais
determinísticos reusando os thresholds da faxina/sanitize:

- `pauta_stalled` (itens parados > 14d) e `inbox_pending` → acúmulo de
  **conteúdo** (o *como*, depois do sim, é a revisão assistida — `/higiene`)
- `backups_old` (> 90d) e `ephemeral_old` (artefatos efêmeros do decidir/acervo
  — HTMLs e a fonte copiada — > 14d) → acúmulo **técnico** (o *como* é o
  módulo `sanitize.md` do core)
- `suggest.update` (o core do workspace — ou o runtime, na falta dele — atrás
  da versão pública em cache, #174) → **update pendente**

Os sinais são **insumo**, não fala: a apresentação segue o contrato do
"Como apresentar" abaixo — **uma** recomendação em linguagem comum, comando
nunca como opção. **Nunca executar** limpeza que pede julgamento por conta
própria. O `/fim` só aponta e delega; não duplica a detecção da higiene nem
roda a sanitização.

Se o runtime não estiver disponível, o agente faz a checagem lendo os arquivos
direto (mesmos thresholds) — a skill é portável.

## Cerca contra overlap com o briefing

O `/fim` é encerramento, não mini-briefing. Ele **NÃO**:

- lê email ou calendário (Gmail/Calendar MCP);
- marca `last-briefing.json` (isso é do briefing, no fim da curadoria rica);
- refaz a proposta/panorama do dia;
- duplica a detecção da higiene (só aponta e delega).

## Como apresentar

Encerrar com: o que foi **registrado** (e onde), o **diário** do dia (link
clicável), o que a **faxina** arrumou — e, se houver acúmulo, **UMA
recomendação em linguagem de gente**, nunca um menu de comandos (#175):

1. **Prioridade: conteúdo > técnica.** Item parado é decisão emperrada; backup
   velho é poeira. O sinal dominante vira A recomendação; o secundário vira uma
   **cláusula** ("aproveito e limpo a poeira técnica junto"), nunca uma segunda
   pergunta.
2. **Comando nunca é opção.** Comando é o *como* — aparece depois do sim,
   quando precisar. A opção nomeia o que acontece, na língua do usuário.
3. **Update pendente cobra na saída (#174):** se `suggest.update` vier `true`,
   a resposta depende do que houve na sessão (semântica canônica: Passo 4 do
   `version-update.md`):
   - o usuário **adiou** no briefing ("depois", silêncio, ou pediu o
     diagnóstico (`c`) e **não decidiu** depois) ou ninguém ofereceu → cobrar
     **uma vez**, como a **última pergunta** da sessão. **Com transporte
     seguro**: "antes de fechar: saiu a X — quer que eu atualize? (~30s)" (o
     comando é o *como* — roda depois do sim, nunca aparece na pergunta).
     **Sem transporte seguro**: não prometer o que não dá pra rodar — a
     cobrança vira a orientação por elo (#108, `version-update.md`), em uma
     linha;
   - o usuário **recusou explicitamente** nesta sessão → silêncio; cobrar de
     novo é nag, não cuidado;
   - **sob compactação** (não dá pra garantir o que foi dito antes): oferecer
     UMA vez, com ressalva curta ("se eu já te perguntei hoje, ignora") — com
     o **mesmo gate de transporte** acima (sem transporte, orientação por elo).
   **Composição com o acúmulo:** são momentos distintos — nunca duas perguntas
   na mesma frase. Primeiro a recomendação de acúmulo (item 1); o update entra
   depois que ela foi respondida ou dispensada, como a última pergunta (ou,
   sem transporte, como a orientação por elo).
4. **Adiar deixa rastro:** se o usuário escolher "amanhã no briefing", gravar o
   item na `PAUTA.md` (Quente): `Revisar N itens parados da pauta (adiado do
   /fim de DD/MM)` — o briefing seguinte lê a pauta e cobra naturalmente. A
   escolha do usuário é a confirmação de escrita.

Exemplo bom:
> "4 itens estão parados na pauta há mais de 2 semanas — quer revisar comigo
> agora (uns 5 min), ou deixo pro briefing de amanhã? Se topar, aproveito e
> limpo a poeira técnica (6 backups velhos) junto."

Exemplo ruim (proibido — foi exatamente o report que gerou o #175):
> "a) /higiene b) /sanitize c) nada por ora"

Se a sessão foi compactada, dizer o que **não** dá pra garantir. Fechar
deixando a próxima sessão limpa: o `/briefing` seguinte já lê
`IDEIAS`/`PAUTA`/`REGISTRO`, então o agente começa up-to-date naturalmente — o
diário é leitura do usuário, não estado do sistema.

## Referências

- `prumo fim --workspace <ws> --format json` — detector de acúmulo (read-only).
- Thresholds reusados: `skills/prumo/references/modules/faxina-thresholds.md`.
- Limpezas que o `/fim` apenas propõe: `skills/higiene/SKILL.md`,
  `skills/prumo/references/modules/sanitize.md`.
