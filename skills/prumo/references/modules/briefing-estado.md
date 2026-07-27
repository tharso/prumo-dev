# Briefing — Estado operacional (F1)

> **module_version: 1.0.0**
>
> Fase F1 da rota fásica do briefing (#180): de onde vem o retrato local
> (pauta, inbox, registro, sinais de faxina) que abre o primeiro tempo.
> Era o Passo 3 do `briefing-procedure.md` (a espinha aponta pra cá).

## Os três transportes, na ordem (semente-primeiro, #197)

**1. Runtime no trilho novo (semente viva):** o JSON de `prumo briefing --workspace <path> --format json` traz o bloco `local_panorama` com tudo que este passo consome. **Gate por CAPACIDADE, não por presença de binário (#206):** confiar na semente exige `local_panorama.schema_version == prumo_local_panorama.v1` **E** `pauta.outras_secoes` presente como lista — runtime velho no PATH = semente incompleta: fallback de leitura direta, nunca semente capenga. A semente carrega: PAUTA por seção — **incluindo `Hibernando`** e **as seções autorais em `pauta.outras_secoes`** (nada da PAUTA fica fora do transporte, #206) — com `text`, `display_text` (esparso: só quando truncado) e `cobrar` parseado (esparso: `state` `future|tomorrow|today|overdue|invalid` + `visible_today`); contagem do `INBOX.md`; cauda do `REGISTRO.md`; sinais mecânicos de faxina. Montar o estado **a partir da semente — não reler `PAUTA.md`/`INBOX.md` integrais pra exibir**.

Arquivo bruto abre em **dois casos apenas**: (1) **edição** — escrever `PAUTA.md`/`REGISTRO.md` no fechamento sempre relê antes; (2) **sinalização** — `payload_completeness.<fonte>.complete == false`, ambiguidade real, **threshold efetivo ≠ declarado pela semente** (override do usuário — ver Faxina abaixo), ou a heurística de aprofundamento (`load-policy.md`, carregar no primeiro uso). O fallback é **por fonte**: pauta incompleta → `PAUTA.md`; `inbox4mobile` com status ≠ `gerado` (enum: `gerado|stale|ausente|invalido|indeterminado`) → `prumo inbox preview` (operação explícita) ou listagem direta; as demais seguem servidas pela semente. Alerta genérico (`degradation`) NÃO é motivo pra releitura integral.

**2. Sem runtime no PATH mas COM o arquivo-semente `.prumo/state/local-panorama.json` (#216 — gravado pelo `prumo seed` de uma máquina com runtime):** usar como semente com gate TRIPLO:

1. **Capacidade**, como na semente viva: `local_panorama.schema_version == prumo_local_panorama.v1` E `pauta.outras_secoes` presente como lista — senão, fallback direto.
2. **DATA**: `local_panorama.generated_for` == a data de HOJE no fuso do workspace — `visible_today` (filtro de cobrança) e sinais de faxina dependem da data, não só dos arquivos; **semente de ontem invalida no mínimo PAUTA e processados** (virada do dia), mesmo com arquivos intactos.
3. **Frescor POR FONTE**: o arquivo carrega `source_mtimes` (mtime de cada fonte no momento da geração) e o `inbox4mobile_manifest` (nome+tamanho+mtime de CADA arquivo do inbox — só "o mais novo" deixaria remoção/renome invisível). Comparar com o estado ATUAL (listagem plana barata de `Prumo/`): fonte cujo retrato difere → **fallback direto daquela fonte** (o resto do arquivo segue valendo); tudo igual → semente inteira vale. Declarar a idade em uma linha quando usar (*"panorama da semente de HH:MM"*).

O agente **NUNCA escreve** esse arquivo — é estado do runtime (#214); consumo é leitura pura.

**3. Sem runtime, sem arquivo-semente, sem `local_panorama` no JSON, ou JSON com erro:** fallback integral — ler `PAUTA.md` e `INBOX.md` como sempre. Nunca inventar dado a partir de JSON parcial (regras do AGENT.md: não fabricar JSON, não simular runtime).

## Faxina (checagem SEMPRE declarada, #217)

**A checagem de faxina declara o resultado SEMPRE (#217 — verificável, não pulável):** a linha obrigatória do primeiro tempo (formato na montagem). O **contrato mínimo da checagem mora AQUI** (sem circularidade: checar não exige abrir o módulo executor); `faxina.md` carrega só quando alguma família está PENDENTE, pra executar. Os NÚMEROS vêm do dono `faxina-thresholds.md` (F1, já carregado) — **defaults + overrides do usuário em `Prumo/Custom/rules/faxina-thresholds.md`** (carregar quando existir); checar contra número fixo ignorando a customização declararia "nada pendente" contra a configuração do usuário. **Override × semente:** a semente pré-calcula com defaults e declara o número usado (`faxina.stale_days_threshold`); se o threshold EFETIVO (com override) diferir do declarado, o pré-calculado daquela família não vale — **recalcular direto da fonte** (ex.: `_processed.json`). **"Nada pendente" só depois de olhar as CINCO famílias do `faxina.md`** — as cinco checagens baratas:

1. **Rotação do REGISTRO** — linhas da tabela acima de `max_items` (a semente já traz o número em `local_panorama.faxina`).
2. **PAUTA→REGISTRO de concluídos** — item marcado concluído (checkbox/riscado/"Concluído") ainda na pauta.
3. **`Referencias/INDICE.md`** — arquivo em `Referencias/` fora da tabela do índice (excluindo os operacionais).
4. **Processados velhos do Inbox4Mobile** — entrada de `_processed.json` com `processed_at` além de `processed_expiry_days` (a semente já traz).
5. **Rotação do `Diario/`** — arquivo com data no NOME além do prazo de rotação do diário.

Atestar limpeza olhando só uma parte é a mesma mentira com crachá novo. Família pendente → carregar `faxina.md` e executar antes de apresentar (ela age sozinha; o resultado entra no briefing em uma linha).

## Filtro de cobrança (a regra é a mesma nos dois caminhos)

Itens com marker `| cobrar: DD/MM` só são elegíveis para o briefing quando a data é hoje, ontem (véspera) ou passada (atrasado). Itens com cobrança para daqui a 2+ dias ficam de fora do briefing — o objetivo é não cobrar antes da hora. Itens sem marker aparecem sempre. Marker ambíguo ou não-parseável: fail-open (mostrar o item). Na semente, `visible_today` já vem calculado por essa regra (e o teste de paridade do runtime trava a equivalência); em leitura direta, aplicar manualmente.

Não persistir estado de briefing entre sessões. A janela temporal de email é fixa em 24h (ver `briefing-canais.md`).
