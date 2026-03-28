# Contrato de Erro, Fallback e Degradacao Elegante

Data de extracao: 2026-03-28

Arquitetura bonita costuma desmaiar no primeiro erro real. Este contrato existe para impedir que o host entregue o cadáver com gravata para o usuário.

## Principio

Quando uma capacidade falha:

1. o produto nao pode mentir;
2. o host nao pode despejar stack trace com boas maneiras;
3. o fluxo nao deve quebrar inteiro se a falha for parcial;
4. `repair` nao deve virar resposta-padrao para qualquer resfriado.

## Objetivo do contrato

Definir:

1. tipos de falha que importam para o produto;
2. o que o runtime deve devolver;
3. como o host deve reagir;
4. quando degradar, quando escalar e quando parar;
5. como registrar o problema sem poluir o palco principal.

## Taxonomia de falhas

### 1. Erro de uso do host

Exemplos:

1. comando com flag invalida;
2. argumento ausente;
3. path errado;
4. repeticao cega do mesmo comando depois de erro explicito.

Regra:

1. isso e falha de adapter/host;
2. o host deve corrigir a chamada;
3. nao deve repetir a mesma linha como papagaio eletrico;
4. nao deve empurrar a culpa para o usuario.

### 2. Falha parcial de capacidade

Exemplos:

1. Gmail falhou, Calendar veio;
2. uma conta conectada veio, a outra caiu;
3. preview do inbox falhou, mas ha preview anterior utilizavel;
4. fonte primaria falhou e fallback ainda existe.

Regra:

1. preservar o que ainda presta;
2. avisar em uma linha curta;
3. manter o fluxo principal de pe;
4. deixar claro o que ficou parcial e o que continua confiavel.

### 3. Falha recuperavel de infraestrutura

Exemplos:

1. bridge indisponivel;
2. snapshot expirado ou ausente;
3. integracao pedindo reautenticacao;
4. arquivo derivado faltando.

Regra:

1. usar fallback previsto quando houver;
2. apontar a acao de recuperacao certa;
3. escalar para `repair`, `auth` ou `align-core` conforme o caso;
4. nao tratar isso como apocalipse de produto.

### 4. Falha estrutural

Exemplos:

1. arquivos recriaveis essenciais sumiram;
2. schema do workspace esta incoerente;
3. runtime nao consegue confiar na propria estrutura base.

Regra:

1. `repair` sobe para o topo;
2. produtividade nao deve fingir normalidade em cima de assoalho podre;
3. o host deve dizer o minimo necessario e conduzir para conserto.

### 5. Falha terminal sem fallback seguro

Exemplos:

1. nem fonte primaria nem fallback entregam dado minimamente confiavel;
2. output esta corrompido;
3. operacao depende de permissao ausente sem rota secundaria.

Regra:

1. o host deve interromper aquela frente especifica;
2. deve oferecer o menor proximo passo util;
3. nao deve improvisar dado;
4. nao deve preencher buraco com prosa ornamental.

## O que o runtime deve devolver

Quando houver falha ou degradacao, o runtime deve preferir:

1. `status` claro (`ok`, `partial`, `error`, `cache`, `needs_auth`, `needs_repair`);
2. `note` curta e humana;
3. `errors[]` ou detalhes estruturados quando fizer sentido;
4. `next_move` coerente com a recuperacao;
5. dados aproveitaveis quando existirem.

O runtime nao deve:

1. despejar traceback para o usuario final;
2. transformar a resposta inteira em confissao tecnica;
3. fingir completude quando so metade veio.

## O que o host deve fazer

### Diante de falha parcial

1. usar o que veio;
2. avisar a falha em uma linha;
3. preservar a condução principal;
4. deixar `next_move` ou acao de recuperacao visivel quando relevante.

### Diante de erro de uso

1. corrigir a chamada;
2. nao insistir na mesma linha;
3. nao dramatizar o erro como se o produto tivesse quebrado.

### Diante de falha estrutural

1. parar a frente atual;
2. priorizar `repair`;
3. ser claro sem despejar jargao.

### Diante de falha terminal sem fallback

1. dizer que aquela frente nao ficou disponivel;
2. dizer o que ainda esta disponivel;
3. oferecer uma acao curta e real.

## Limites de retry e silencio

### Retry

1. erro de uso explicito: zero repeticoes cegas;
2. falha transiente local e curta: no maximo uma nova tentativa automatica, se o risco for baixo;
3. integracao externa lenta ou falhando: nao ficar rodando girador de ansiedade em segundo plano.

### Silencio

1. silencio total sobre falha parcial e proibido;
2. o aviso deve caber, idealmente, em uma linha;
3. diagnostico longo fica para `context`, `doctor` ou log tecnico, nao para o centro da conversa.

Silencio operacional e so bug com boa postura.

## Relacao com documentacao

Registrar em `_state/` ou estado tecnico quando:

1. a falha afeta integracao persistente;
2. a origem deve influenciar a proxima decisao do runtime;
3. o sistema precisa lembrar que ja tentou e tropeçou.

Registrar no `REGISTRO.md` quando:

1. houve efeito real no trabalho do usuario;
2. a degradacao alterou uma decisao;
3. uma operacao foi concluida em fallback.

Nao registrar em arquivo autoral quando:

1. o erro e puramente interno e transitorio;
2. nada mudou para a vida do usuario.

## Escalada para repair

Escalar para `repair` quando:

1. estrutura do workspace estiver quebrada;
2. arquivo derivado canônico faltar;
3. drift do core comprometer o contrato do host;
4. a falha nao for de integracao externa, e sim de estrutura local.

Nao escalar para `repair` quando:

1. o problema for reautenticacao;
2. a fonte externa estiver cansada mas fallback seguir vivo;
3. o host errou a chamada.

## Exemplos minimos

### Invocacao curta

Bom:

`O runtime pediu reautenticacao do Google. O resto do workspace esta de pe. Proximo passo: \`prumo auth google --workspace ...\`.`

Ruim:

`HTTP 401 invalid_grant trace_id=... stack=...`

### Briefing com falha parcial

Bom:

`Agenda veio inteira. Email da conta trabalho caiu e eu segui com o que ainda respirava.`

Ruim:

`Falha ao inicializar providers: partial snapshot merge exception.`

### Inbox preview caiu

Bom:

`O preview novo falhou, mas ainda ha um anterior utilizavel. Vou usar esse e marcar que pode estar defasado.`

Ruim:

`Nao foi possivel continuar.`

## Fronteira

Este contrato define:

1. comportamento compartilhado de falha;
2. limites de retry;
3. criterios de degradacao;
4. relacao entre erro e proximo movimento.

Este contrato nao define:

1. tom autoral completo do host;
2. UI visual de erro;
3. detalhes de log interno por provider.
