# Briefing — Estado operacional (F1)

> **module_version: 1.0.0**
>
> Fase F1 da rota fásica do briefing (#180): de onde vem o retrato local
> (pauta, inbox, registro, sinais de faxina) que abre o primeiro tempo.
> Era o Passo 3 do `briefing-procedure.md` (a espinha aponta pra cá).

## Os três transportes, na ordem (semente-primeiro, #197)

**1. Runtime no trilho novo (semente viva):** o JSON de `prumo briefing --workspace <path> --format json` traz o bloco `local_panorama` com tudo que este passo consome. **Gate por CAPACIDADE, não por presença de binário (#206):** confiar na semente exige `local_panorama.schema_version == prumo_local_panorama.v1`, `pauta.outras_secoes` presente como lista e `indice_referencias.schema` (#261) — runtime velho = semente incompleta: fallback de leitura direta, nunca semente capenga. A semente carrega: PAUTA por seção — **incluindo `Hibernando`** e **as seções autorais em `pauta.outras_secoes`** (nada da PAUTA fica fora do transporte, #206) — com `text`, `display_text` (esparso: só quando truncado) e `cobrar` parseado (esparso: `state` `future|tomorrow|today|overdue|invalid` + `visible_today`); contagem do `INBOX.md`; cauda do `REGISTRO.md`; sinais mecânicos de faxina. Montar o estado **a partir da semente — não reler `PAUTA.md`/`INBOX.md` integrais pra exibir**.

Arquivo bruto abre em **dois casos apenas**: (1) **edição** — escrever `PAUTA.md`/`REGISTRO.md` no fechamento sempre relê antes; (2) **sinalização** — `payload_completeness.<fonte>.complete == false`, ambiguidade real, ou a heurística de aprofundamento (`load-policy.md`, carregar no primeiro uso). O fallback é **por fonte**: `faxina_override` divergente (editado/removido após o `seed`) **invalida o bloco `faxina` inteiro** — carregar o doc + o override atual, recompor thresholds e **recontar** o que depende deles; pauta incompleta → `PAUTA.md`; `inbox4mobile` com status ≠ `gerado` (enum: `gerado|stale|ausente|invalido|indeterminado`) → `prumo inbox preview` (operação explícita) ou listagem direta; as demais seguem servidas pela semente. `degradation` genérico não motiva releitura integral.

**2. Sem runtime no PATH mas COM o arquivo-semente `.prumo/state/local-panorama.json` (#216 — gravado pelo `prumo seed` de outra máquina):** usar com gate TRIPLO:

1. **Capacidade**, como na semente viva — senão, fallback direto.
2. **DATA**: `local_panorama.generated_for` == a data de HOJE no fuso do workspace — `visible_today` (filtro de cobrança) e sinais de faxina dependem da data, não só dos arquivos; **semente de ontem invalida no mínimo PAUTA e processados** (virada do dia), mesmo com arquivos intactos.
3. **Frescor POR FONTE**: o arquivo carrega `source_mtimes` (mtime de cada fonte — inclusive o override e o `INDICE.md` + manifesto de `Referencias/`) e o `inbox4mobile_manifest` (nome+tamanho+mtime de CADA arquivo; só "o mais novo" deixaria remoção/renome invisível). Comparar com o estado ATUAL (listagem plana barata de `Prumo/`): fonte cujo retrato difere → **fallback direto dela** (o resto segue valendo); tudo igual → semente inteira vale. Declarar a idade ao usar (*"panorama da semente de HH:MM"*).

O agente **NUNCA escreve** esse arquivo — estado do runtime (#214); consumo é leitura pura.

**3. Sem runtime, sem arquivo-semente, sem `local_panorama` no JSON, ou JSON com erro:** fallback integral — ler `PAUTA.md` e `INBOX.md` como sempre. Nunca inventar dado a partir de JSON parcial (regras do AGENT.md: não fabricar JSON, não simular runtime).

## Faxina (checagem SEMPRE declarada, #217)

**A checagem de faxina declara o resultado SEMPRE (#217 — verificável, não pulável):** a linha obrigatória do primeiro tempo (formato na montagem). O **contrato mínimo da checagem mora AQUI** (sem circularidade: checar não exige abrir o módulo executor); `faxina.md` carrega só quando alguma família está PENDENTE, pra executar. Os NÚMEROS vêm de `faxina.thresholds` da semente (#258): **efetivos**, com o override (`Custom/rules/faxina-thresholds.md`) já aplicado pelo runtime; `thresholds_source` diz a origem; `ignored_keys` lista o que o override trazia fora do vocabulário (reportar, nunca adivinhar). Sem semente, com `faxina.schema` ≠ `prumo_faxina_thresholds.v1` (o único aceito) ou com override divergente: carregar o doc **+ o override atual** — os três caminhos que trazem `faxina-thresholds.md` pra rota. **"Nada pendente" só depois de olhar as CINCO famílias do `faxina.md`** — as cinco checagens baratas:

1. **Rotação do REGISTRO** — linhas da tabela acima de `max_items` (a semente já traz o número em `local_panorama.faxina`).
2. **PAUTA→REGISTRO de concluídos** — item marcado concluído (checkbox/riscado/"Concluído") ainda na pauta.
3. **`Referencias/INDICE.md`** — `indice_referencias.decisao` (#261): `bloquear` = pendente e **proibido reindexar** (higiene resolve); `reindexar` = pendente; `ok` = limpa. Sem o bloco: comparar a **coluna `Arquivo`** e a lacuna do rodapé — só a diferença de conjuntos deixa passar índice truncado sem ficha órfã.
4. **Processados velhos do Inbox4Mobile** — entrada de `_processed.json` com `processed_at` além de `processed_expiry_days` (a semente já traz).
5. **Rotação do `Diario/`** — arquivo com data no NOME além do prazo de rotação do diário.

Atestar limpeza olhando só uma parte é mentira com crachá novo. Família pendente → carregar `faxina.md` e executar antes de apresentar (age sozinha; o resultado vira uma linha no briefing).

## Filtro de cobrança (a regra é a mesma nos dois caminhos)

Itens com marker `| cobrar: DD/MM` só são elegíveis para o briefing quando a data é hoje, ontem (véspera) ou passada (atrasado). Itens com cobrança para daqui a 2+ dias ficam de fora — não cobrar antes da hora. Itens sem marker aparecem sempre. Marker ambíguo: fail-open (mostrar). Na semente, `visible_today` já vem calculado por essa regra (e o teste de paridade do runtime trava a equivalência); em leitura direta, aplicar manualmente.

Não persistir estado de briefing entre sessões. Janela de email fixa em 24h (`briefing-canais.md`).
