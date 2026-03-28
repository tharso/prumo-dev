# Diretriz de Granularidade das Capacidades

Data de extracao: 2026-03-28

Capability demais e como talher de restaurante pretensioso: bonito na foto, irritante na vida. Capability gorda demais faz o runtime virar narrador com CNPJ. O ponto bom fica no meio, e precisa ser dito com clareza para nao virar culto de gosto pessoal.

## Principio

Uma capacidade boa entrega:

1. uma unidade de valor reconhecivel pelo produto;
2. latencia suportavel;
3. dados estruturados suficientes para o host agir;
4. pouca necessidade de encadear chamadas cosmeticas.

## Sinais de capacidade atomica demais

Se a "capacidade" faz so uma destas coisas, desconfie:

1. retorna um pedacinho de estado que ainda exige varias consultas irmas para virar decisao;
2. existe apenas para espelhar uma funcao interna sem valor de produto claro;
3. obriga o host a fazer mais de 3 chamadas para compor uma resposta banal;
4. aumenta latencia sem reduzir ambiguidade.

Exemplo ruim:

1. `get_hot_items`
2. `get_ongoing_items`
3. `get_inbox_count`
4. `get_google_status`
5. `get_last_briefing_at`
6. `rank_candidate_actions`

Isso parece modular. Na pratica, entrega um quebra-cabeca e chama isso de API.

## Sinais de capacidade gorda demais

Tambem desconfie quando a capacidade:

1. devolve texto final praticamente pronto para o usuario;
2. mistura coleta, decisao, prosa e apresentacao;
3. esconde efeitos colaterais demais num bloco opaco;
4. impede o host de adaptar a experiencia ao ambiente.

Exemplo ruim:

1. `run_full_morning_experience_and_reply_to_user`

Isso nao e capability. E runtime pedindo o palco de volta.

## Unidade preferida

A unidade preferida e:

1. composta o bastante para representar uma acao de produto;
2. enxuta o bastante para nao sequestrar a UX;
3. estruturada o bastante para o host nao adivinhar.

Exemplos bons:

1. `start`
2. `briefing`
3. `inbox preview`
4. `repair`
5. `context-dump`

Essas capacidades ja entregam valor reconhecivel sem exigir procissao de pecinhas.

## Regra pratica de tool-chaining

Para um fluxo comum de produto:

1. ideal: 1 chamada principal;
2. aceitavel: 2 chamadas quando a segunda decorre de escolha clara do usuario ou do `next_move`;
3. suspeito: 3 chamadas para montar uma resposta simples;
4. ruim: 4 ou mais chamadas so para descobrir o que fazer.

Se um host agentico precisar de 8 marteladas para dizer "vamos continuar pelo item quente", a arquitetura errou de religião.

## Payload composto vs micro-capacidades

Quando houver orquestracao de produto, preferir:

1. payload composto;
2. sections estruturadas;
3. `actions[]`;
4. `next_move`;
5. contratos de selecao e documentacao.

Quando houver operacao tecnica isolada, preferir:

1. capacidade mais pontual;
2. saida objetiva;
3. minimo de prosa.

## Compatibilidade com hosts fortes

Hosts fortes que operam bem em arquivos locais nao devem ser obrigados a usar wrapper pesado para tudo.

Regra:

1. integracao externa, snapshot, auth e estado tecnico complexo combinam com runtime;
2. leitura e edicao local simples de Markdown nao precisam virar missa Python por dogma.

## Latencia aceitavel por fluxo

### Invocacao curta

1. deve preferir uma chamada;
2. pode devolver payload estruturado rico;
3. nao deve exigir fan-out de consultas para decidir o proximo passo.

### Briefing

1. pode ser mais pesado porque ja e uma acao composta;
2. ainda assim deve entregar sections e acoes prontas;
3. nao deve obrigar o host a chamar micro-capacidades para montar panorama, proposta e proximo movimento.

### Inbox

1. preview pode ser capacidade dedicada;
2. commit pode ser outra;
3. nao faz sentido dividir triagem em quinze instrumentos de sopro.

## Regra de bolso

Pergunta util:

"Se eu tirar esta capacidade, o host perde uma unidade de valor reconhecivel ou so deixa de acessar uma tripa interna?"

Se for tripa interna, provavelmente esta atomica demais.

Se a capacidade ja fala quase como o produto inteiro, provavelmente esta gorda demais.
