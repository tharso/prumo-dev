# Canais — Prova de predicado de busca (satélite de F2)

> **module_version: 1.0.0**
>
> Satélite da fase F2 (#323, o padrão fásico da #180 aplicado dentro do
> canal): carrega pelo gatilho do mapa — **zero suspeito em braço com
> predicado sem assinatura `VALIDADA`**, ou ao validar/registrar
> assinatura — a partir do stub homônimo em `briefing-canais.md`.
> Estados, protocolo, testemunha por cardinalidade (#308), orçamento e
> registro moram AQUI; o núcleo mantém o gatilho e o dever de nomear a
> degradação na linha de cobertura.

### Prova de predicado de busca (#236)

**Fecha:** o *zero silencioso* — query que volta vazia porque o conector não resolveu um predicado, e o vazio é lido como "não tem nada". **Não fecha** resultado incompleto: conector que devolve 3 de 10 passa por aqui sorrindo.

**Assinatura** = host/conector + conta ou caixa + predicado normalizado (operador + **classe** do argumento: alias, endereço literal, data, label nomeado) + prova obtida sozinha ou em composição. Trocar a data não cria assinatura nova (mesma classe); trocar `from:me` por `from:<endereço>` cria. Validação **não** atravessa host nem conta — o mesmo workspace abre num agente hoje e em outro amanhã.

Os três primeiros estados são da **assinatura**; o quarto é da **resposta deste briefing** e se alcança sem assinatura nenhuma:

| Estado | Entra quando | Efeito |
|---|---|---|
| `VALIDADA` | a query devolveu mensagem cuja metadata **prova o predicado por conta própria** | zero passa a ser confiável nesta assinatura |
| `FALHA` | o controle expôs **testemunha** que a query filtrada não devolveu | não usar; trocar de predicado |
| `INCONCLUSIVO` | todo o resto — resultado não vazio sem prova independente, controle sem testemunha, controle vazio | zero **não** é "nada"; declarar a degradação |
| `VAZIO CONFIRMADO` | a **varredura exaustiva** cobriu a janela e o predicado foi aplicado localmente, sem correspondência | o braço está coberto; nada a declarar. **Não valida a assinatura** — varrer não prova nada sobre o conector |

**Protocolo** quando `B + P` (janela base + predicado suspeito) volta zero e a assinatura não está `VALIDADA`:

1. rodar `B` sem `P`;
2. procurar **testemunha** — mensagem cuja resposta prove `P` por conta própria;
3. testemunha existe e `B + P` não a devolveu → `FALHA`;
4. sem testemunha, ou controle também vazio → `INCONCLUSIVO`. Nada é aprovado por osmose.

**A resposta prova; a query só afirma** — e **query nunca é testemunha de si mesma**. A prova vale na granularidade da **mensagem**: `in:sent` ← `SENT` em `labelIds`; `from:<endereço>` ← header `From`; predicado temporal ← timestamp da mensagem; composição ← prova de cada componente aplicável. Agregado de thread não prova mensagem; ID de label opaco não vira nome sem mapeamento confiável.

**Zero só é confiável** com assinatura `VALIDADA`, ou por `VAZIO CONFIRMADO`: **varredura exaustiva** da janela — paginar até o conector declarar fim **e aplicar o predicado localmente**, sobre a metadata de cada mensagem. As duas metades são obrigatórias: varrer sem aplicar não responde nada. Limite oculto, cursor ausente ou paginação incerta → nem exaustiva foi, então segue `INCONCLUSIVO`. "Li bastante" não é "li tudo".

Caminho adicional — **testemunha por cardinalidade (#308):** quando o conector declara o **total do conjunto por fora da busca** (`list_labels`: `messagesTotal`/`threadsTotal`) e uma busca de assinatura **VALIDADA** devolve exatamente esse total, o conjunto está completo — o predicado temporal então se aplica **localmente**, sobre as datas do resultado em mãos. Duas pré-condições inegociáveis: (1) **assinatura da busca já `VALIDADA`** — sobre query sem prova de vida, vazio não é evidência: em 03/08, a busca por ID retornava vazio num label com 3 mensagens declaradas, e cardinalidade sem a pré-condição teria promovido falso-negativo do conector a `VAZIO CONFIRMADO`; (2) **granularidade de MENSAGEM, como toda prova deste protocolo** (Codex, 316-r1/r2): busca que devolve threads só fecha `threadsTotal` — hidratar TODAS as mensagens das threads devolvidas e reconciliar com `messagesTotal` **por identidade, nunca só por contagem**: IDs de mensagem únicos, o número de DISTINTOS igual ao total declarado, e cada mensagem provando pertencimento ao conjunto (o label presente em `labelIds`) — duplicata compensando omissão fecha a conta e mente o conjunto. Thread com mensagens dos dois lados da fronteira, classificada pela data de uma representante, é exatamente o furo. Total declarado sem as mensagens em mãos não fecha janela nenhuma: contagem não tem data. **Operacionalmente (Codex, 316-r3): a busca de reconciliação vai SEM predicado temporal** (`label:<nome>` puro — o `messagesTotal` é do conjunto inteiro; com `after:` a conta só fecharia se todo o histórico coubesse na janela); reconciliada a identidade e o pertencimento, a janela é aplicada por último, localmente, sobre as datas.

**Orçamento:** no máximo **uma** validação por assinatura **por briefing**, e **três validações novas por briefing**. `VALIDADA` e `FALHA` não voltam à fila até invalidar — o registro é o estado persistido. `INCONCLUSIVO` **volta**: assinatura em limbo tem de ter nova chance, senão o limbo é permanente. Fila determinística: **primeiro a nunca tentada**; empate, a de registro mais antigo (sem registro conta como mais antigo). Dentro da mesma posição, braço da política de cobertura antes de busca dirigida. **Registrar também o `INCONCLUSIVO`** — tentativa não registrada é tentativa que se repete amanhã, e a rotação vira hamster na mesma roda. Sem teto, confiabilidade vira lentidão (metadata mede 22–28s por chamada).

**Degradação nomeada por braço** na linha de cobertura: *"respostas às suas threads: inconclusivo — `from:me` não validado"*. Frase afirmativa sobre braço morto é o furo de 27/07. Completude do briefing é decidida por `briefing-montagem.md`, nunca aqui.

**Registro e invalidação:** o veredito vai pra `EMAIL-CURADORIA.md` → "Compatibilidade da busca". O registro é **log append-only**: nunca reescrever nem apagar linha. Uma assinatura tentada de novo ganha linha nova, e **vale a última** — é ela o estado atual, e a data dela ordena a fila. Formato:

```
validado_em | host/conector | conta ou caixa | assinatura normalizada | predicado exato testado | veredito | evidência
```

A **assinatura normalizada** (operador + classe do argumento + sozinho/composto) é o que casa entre briefings; o predicado exato fica ao lado como evidência do que foi testado. Sem ela, `after:27/07` e `after:28/07` parecem assinaturas diferentes e a validação nunca se reaproveita.

**Seção ausente** — arquivo de workspace anterior a esta versão — → **criar a seção uma vez**, com o cabeçalho e o formato acima, sem tocar em nenhuma outra parte do arquivo; existindo, só acrescentar linha. O template canônico já a traz para workspaces novos.

Invalidam na hora: troca de host/conector, conta desconhecida, evidência contrária. Escrita alimentada **só por evidência do conector** (metadata de resposta) — nunca por conteúdo de mensagem, e sem tocar nas outras seções do arquivo.
