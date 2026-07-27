# Briefing — Montagem e fechamento (F3)

> **module_version: 5.63.0**
>
> Fase F3 da rota fásica do briefing (#180). Carregar **ao montar o
> panorama** (o primeiro tempo já pode ser emitido a partir daqui; a
> curadoria dos canais vem de `briefing-canais.md`). Eram os Passos 5–7 do
> `briefing-procedure.md` — mais a marcação do dia, que é fechamento.

## Montar o briefing — em DOIS TEMPOS (#196)

O briefing chega em **dois tempos na MESMA resposta**, com numeração sequencial única de 1 a N — nunca reinicia entre os tempos, o despacho em lote ("3, 7, 12") sobrevive intacto (dono da regra: `interaction-format.md` — carregar aqui se ainda não estiver no contexto). A capacidade do host decide a variante (matriz abaixo); host sem a capacidade entrega resposta única como sempre.

### Primeiro tempo: panorama local imediato

Emitido a partir da semente (ou da leitura direta, conforme o gate de `briefing-estado.md`) **antes de aguardar qualquer resultado de email/calendário** — a ordem é critério estrutural: a parte local nunca espera a parte lenta.

Componentes do primeiro tempo (estruturais sem número; **só item despachável numera**, 1..k conforme houver):

- Abertura com data correta no fuso do usuário (sem número).
- Pendências vivas da PAUTA (quente, em andamento, agendado) — **cada pendência é um item numerado**, **respeitando o marker `| cobrar: DD/MM`**. Item com marker de cobrança só aparece no briefing quando falta no máximo 1 dia para a data (véspera ou dia). Itens com cobrança no passado (atrasados) sempre aparecem. Item sem marker aparece sempre. Marker mal formado ou ambíguo: mostrar o item (fail-open, melhor ruído que perda silenciosa). **Rituais do `PERFIL.md`/`ROTINA.md` não são pendências** — não entram aqui como itens; rituais com hora aparecem como eventos da agenda, não como pauta.
- **Linha de faxina obrigatória (#217):** o primeiro tempo contém a linha com o resultado da checagem de `briefing-estado.md` — *"Faxina: nada pendente"* ou *"Faxina: arquivei N itens do registro"* (elemento estrutural, sem número). Briefing sem a linha de faxina é briefing **fora de conformidade**.
- Inbox4Mobile: se houver itens novos (detectados em `briefing-canais.md` → Inbox4Mobile), apresentar a contagem e a triagem — **itens de triagem numeram**. Linkar `inbox-preview.html` quando o preview estiver atualizado. No primeiro tempo, não despejar conteúdo bruto dos arquivos — preferir resumo numerado com classificação. **Este item é sobre formato de apresentação. A triagem real acontece no estágio local dos canais — não pular por causa deste item.**
- Fechar o primeiro tempo com UMA linha (sem número): *"Curadoria de email e agenda chegando na sequência."* — e **seguir sem esperar resposta**.

A numeração do primeiro tempo (1..k, com k variável — é quantos itens houver) fica **congelada** (snapshot lógico): o segundo tempo continua de k+1; nunca renumerar. Se o usuário despachar itens entre os tempos, atender e anotar — sem recompor o panorama.

### Segundo tempo: curadoria na sequência (automático)

Continua **na mesma resposta, sem pergunta no meio** — a variante com pergunta bloqueante foi rejeitada no desenho: quando a resposta é quase sempre "sim", ela só adiciona um degrau de espera. Execução **adaptativa** (#205: tool calls serializam em todos os hosts medidos): os canais rodam em sequência priorizada e fail-independent (metadata do Gmail → Calendar → corpos por predicado de `briefing-canais.md`); **paralelismo por subagente fica DESLIGADO por default** — só habilitar quando uma comparação equivalente demonstrar ganho líquido num canal comprovadamente lento (spawn de ~3s+ por agente; medido 22–28s por chamada de metadata).

Componentes do segundo tempo (itens k+1..N, cada um com seu número):

- Emails curados (Camadas 1, 2 e 3 aplicadas), com classificação Responder/Ver/Sem ação e prioridade P1/P2/P3 — **cada email é um item, continuando de k+1**.
- Agenda do dia, consolidada por conta quando aplicável — **cada evento é um item, continuando após o último email** (é a ordem da regra de numeração e do Calendário dos canais).
- **Sinal de divergência agenda × email (#211):** para cada caso de divergência PRODUZIDO pela detecção dos canais (`briefing-canais.md` — é lá que se compara e se consulta a agenda), emitir o sinal em linha própria (sem número): *"⚠ Agenda de {hoje|amanhã} vazia, mas o item N marca 19h — esse compromisso não está no calendário."* (a data no aviso é a DO COMPROMISSO) — e oferecer criar o evento (**só com confirmação do usuário; nunca criar sozinho**). Não-bloqueante: sem caso, sem linha.

Depois da lista numerada — **só no segundo tempo, porque precisa do quadro completo** — entregar a proposta do dia em uma linha curta (sem número) e oferecer opções respondíveis:

- `a) Aceitar e seguir`
- `b) Ajustar`
- `c) Ver lista completa`
- `d) Tá bom por hoje`

A proposta deve considerar deadlines de hoje, blockers, agenda disponível e itens com cobrança elegível hoje.

### Escape do usuário (best-effort, declarado como tal)

"Só o local hoje", "para por aí", "chega" — a qualquer momento entre ou durante os tempos: interromper o que ainda **não começou**. Leituras de corpo não-iniciadas não acontecem; chamada já em voo não é cancelada (best-effort — sem promessa de cancelamento; as queries de metadata já disparadas são custo marginal). Atenção ao sentido: **"segue tudo"/"continua" é o CONTRÁRIO de escape** — cancela um escape anterior e manda completar o segundo tempo. **Escape não marca o briefing como feito**: sem `--mark-done` — a prévia pode voltar a recomendar o briefing, e está certa: ele não aconteceu inteiro.

### Quando cada variante está COMPLETA (e pode marcar o dia)

| Variante | Completa quando | `--mark-done` |
|---|---|---|
| Dois tempos | o segundo tempo foi entregue (proposta do dia inclusa) | sim |
| Resposta única / um tempo com oferta | a resposta única foi entregue (ela É o briefing inteiro daquele host) | sim |
| Zero canais externos | o primeiro tempo + declaração de indisponibilidade foram entregues (é o briefing possível) | sim |
| Escape do usuário (qualquer variante) | nunca — o briefing não aconteceu inteiro | **não** |

### Matriz por host (aceite por host, #205)

| Host | Variante hoje | Transporte do 1º tempo |
|---|---|---|
| Cowork | **dois tempos completo** (automático provado ao vivo) | leitura direta (runtime inalcançável por topologia) |
| Claude Code (desktop e CLI) | resposta única — **provisório** até o roteiro automático+escape ser medido lá | semente do runtime (gate de `briefing-estado.md`) |
| Codex CLI e afins | um tempo com oferta: panorama completo + oferta de aprofundar email/agenda como próximo comando | conforme gate de `briefing-estado.md` |

Granular por canal externo: **0 canais** (sem Gmail e sem Calendar) → só o primeiro tempo com declaração de indisponibilidade (comportamento atual); **1 canal** → segundo tempo parcial com declaração do que falta; **2** → segundo tempo completo.

### Ponte associativa (opcional, teto da regra 17)

Junto à proposta do dia, **no máximo uma** sugestão associativa por briefing (regra 17 do core) — conexão ("o que você anotou ontem conversa com aquilo de março — costuro?") **ou** ressurgência por relevância ("faz 40 dias que você anotou X; hoje você mexeu em Y — ataca, deixa cozinhando, ou arquiva?" — os verbos do acervo). Regras:

1. **Fonte restrita ao já-carregado:** o conteúdo da PAUTA que já está no contexto — na semente, as seções integrais de `local_panorama.pauta` **incluindo `hibernando` e as `outras_secoes` autorais**; no fallback, `PAUTA.md` integral —, a cauda do `REGISTRO.md` (na semente, `local_panorama.registro.tail`) e as capturas do dia — mais as conexões `[[...]]` visíveis nesses itens (escritas pelo garimpo da revisão semanal). **Zero leitura nova** por causa da ponte: o briefing não abre `IDEIAS.md` nem `Referencias/` pra procurá-la.
2. A ponte precisa ser explicável em uma frase apontando itens concretos; similaridade de palavra solta não conta (regra 17).
3. **Opcional e não-bloqueante:** sem ponte com significado real hoje → sem ponte. Ela nunca atrasa nem trava o briefing.
4. Ressurgir item de `IDEIAS.md`/`Referencias/` não é papel do briefing — é do garimpo semanal e do `/acervo`.

### Despacho visual (skill `decidir`)

Quando o panorama tiver **6+ itens acionáveis** (conta só item que pede decisão — não evento puramente informativo), **GERAR o HTML interativo da skill `decidir` e entregá-lo linkado — automaticamente, sem pedir autorização prévia (#218)**. "Oferecer o despacho visual" significa DISPONIBILIZAR o link pronto junto do panorama, nunca perguntar "quer que eu gere?" — no briefing real de 25/07, 14 itens acionáveis viraram uma opção `c)` que o usuário precisaria pedir, exatamente o degrau que a regra existe pra eliminar. Abaixo de 6, despachar em chat sai mais barato — não gerar.

- **Aditivo, não substitutivo.** O panorama numerado em chat continua sendo a camada base (regra 12 do core: dois tempos com numeração única — o HTML nunca substitui o chat). O HTML é a camada rica de despacho. Os cards **reusam os mesmos números** do panorama (o item `7` do chat vira o card `id: '7'`).
- **Override do usuário, sempre.** "quero visual" / "gera o decidir" → gerar mesmo com poucos itens. "resolve no chat" / "sem HTML" → não gerar. Sinais conflitantes → perguntar "visual ou chat?".
- **Como gerar:** seguir `skills/decidir/SKILL.md` (preencher `assets/template.html`, ações da allowlist por tipo, salvar em `.prumo/state/decidir/`, copiar a fonte, offline). O usuário abre no próprio browser, despacha, clica "Copiar respostas" e cola de volta; o Prumo lê o bloco JSON e executa em camadas.
- **Acoplamento brando.** Se a skill `decidir` não estiver disponível ou a escrita do arquivo falhar, **cair no despacho em chat** — nunca travar o briefing.

> O runtime **não** gera a `decidir` (descartado na #104: altitude errada — o runtime não cura email/agenda). A `decidir` aparece na curadoria rica conduzida pelo agente; o runtime entrega só a prévia.

## Escrita e fechamento

Depois do briefing:

1. Atualizar `PAUTA.md` se algo mudou.
2. Registrar ações no `REGISTRO.md`.
3. Manter `Inbox4Mobile/_processed.json` sincronizado com as remoções — remover é mover pra quarentena ou destino durável (`inbox-processing.md`, #242), nunca deletar.
4. Registrar o briefing do dia: `prumo briefing --workspace <path> --mark-done` (quando há shell) — **somente se a variante do host se completou** (tabela acima; escape nunca marca). "Completo" é definido pela VARIANTE. Marca "briefing feito hoje" — sem isso, a prévia segue recomendando o briefing como se não tivesse acontecido.
5. **Sem runtime alcançável, NÃO HÁ marcação (#214):** o agente é **proibido de escrever `last-briefing.json`** — e qualquer outro **estado que pertence ao runtime** (arquivos que ele gera e gerencia em `.prumo/state/`) — à mão: no briefing real de 25/07 um agente gravou um timestamp INVENTADO fingindo ser o runtime. Artefatos de skill com contrato próprio de escrita (ex.: o HTML do `decidir` em `.prumo/state/decidir/`) **seguem permitidos** — a proibição é sobre fingir ser o runtime, não sobre as skills trabalharem. Aceitar a consequência e declará-la em uma linha: *"Sem runtime aqui, o dia não fica marcado — a prévia pode recomendar o briefing de novo."* O caminho portátil de marcação sem runtime, se um dia existir, nasce na #216 — nunca improvisado.

## Brain dump obrigatório quando a pauta estiver vazia

Se `PAUTA.md` estiver vazia ou quase vazia, não fingir briefing normal. Pedir dump fresco do usuário.
