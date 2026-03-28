# Backlog operacional de issues: capability-backend e experiencia multi-host

Status: rascunho revisado para abertura no GitHub

Data: 2026-03-28

Relacionado:

1. [PRUMO-CAPABILITY-BACKEND-ARCHITECTURE.md](/Users/tharsovieira/Documents/DailyLife/Prumo/PRUMO-CAPABILITY-BACKEND-ARCHITECTURE.md)
2. [LOCAL-RUNTIME-TRANSITION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/LOCAL-RUNTIME-TRANSITION-PLAN.md)
3. [HOST-ADAPTER-IMPLEMENTATION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/HOST-ADAPTER-IMPLEMENTATION-PLAN.md)
4. [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md)
5. [REPO-WORKSPACE-JURISDICTION.md](/Users/tharsovieira/Documents/DailyLife/Prumo/REPO-WORKSPACE-JURISDICTION.md)

Observacao:

Artefatos de oficina como handover e revisoes cruzadas vivem na `.workbench/` do repo e seguem fora do material versionado do produto. Eles informam este backlog, mas nao sao parte dele.

## 1. Como usar este backlog

Este arquivo nao e o backlog do usuario final. E um rascunho de execucao para abrir issues no GitHub com escopo claro.

Objetivo:

1. evitar que a implementacao comece com ordem errada;
2. separar produto de infraestrutura de desenvolvimento;
3. incorporar as criticas de Claude e Antigravity antes de cortar metal;
4. garantir que o GitHub vire a memoria duravel da execucao.

## 2. Ordem de execucao recomendada

1. abrir epico-mãe
2. abrir ADRs estruturais
3. decidir o destino do `cowork-plugin`
4. auditar estado atual
5. extrair canon do plugin com inventario de sabedoria operacional
6. definir contrato de orquestracao compartilhada
7. definir portabilidade de persona
8. definir contrato de erro, fallback e granularidade de capacidades
9. definir governanca documental minima
10. redesenhar runtime
11. especificar adapters por host
12. so depois atacar onboarding
13. Slack por ultimo

## 3. Epico-mãe

### Issue 1

**Titulo**

`Epic: Reorientar o Prumo para UX host-native com runtime como backend de capacidades`

**Tipo**

Epico

**Objetivo**

Consolidar a reorientacao arquitetural do Prumo para:

1. `Workspace` unico e canonicamente estruturado;
2. runtime como backend de capacidades;
3. orquestracao compartilhada entre host e runtime;
4. experiencia principal nos hosts;
5. governanca documental como subsistema central;
6. transicao segura a partir do legado plugin-first.

**Checklist sugerido**

1. ADR da arquitetura capability-backend
2. ADR da governanca documental
3. ADR do protocolo multi-host de desenvolvimento
4. decisao sobre o destino do `cowork-plugin`
5. auditoria do estado atual
6. extracao do canon
7. contrato de orquestracao
8. portabilidade de persona
9. redesenho do runtime
10. adapters finos por host
11. onboarding/install amigavel
12. adapter Slack corporativo

**Criterio de aceite**

O epico so fecha quando o repositorio tiver:

1. canon explicito;
2. runtime rebaixado para capacidades;
3. orquestracao compartilhada definida;
4. pelo menos Codex e Claude operando sobre a mesma base;
5. governanca documental formalizada.

## 4. ADRs estruturais

### Issue 2

**Titulo**

`ADR-002: Prumo como backend de capacidades com experiencia multi-host`

**Tipo**

Arquitetura

**Objetivo**

Registrar oficialmente que:

1. a experiencia mora no host;
2. o runtime fornece capacidades;
3. o `Workspace` raiz e a memoria viva do sistema;
4. `AGENT.md` e direcao arquitetural, nao dogma prematuro;
5. o produto nao deve mais tratar runtime como narrador principal.

### Issue 3

**Titulo**

`ADR-003: Governanca documental, memoria local e limpeza com delegacao otimista`

**Tipo**

Arquitetura

**Objetivo**

Formalizar:

1. jurisdicao dos arquivos;
2. tipos de memoria do sistema;
3. nomes intuitivos;
4. indices humanos e tecnicos;
5. limpeza automatica vs assistida;
6. delegacao otimista quando o risco editorial for baixo;
7. escalacao quando higiene e ignorada repetidamente.

### Issue 4

**Titulo**

`ADR-004: Protocolo multi-host de desenvolvimento e handover interno`

**Tipo**

Processo de desenvolvimento

**Objetivo**

Fixar que:

1. `.workbench/HANDOVER.md` e ferramenta interna de oficina;
2. nao faz parte do produto;
3. serve para coordenacao entre Codex, Claude e Antigravity;
4. toda decisao duravel deve subir para GitHub.

## 5. Decisoes bloqueantes e auditoria

### Issue 5

**Titulo**

`Decidir o destino do cowork-plugin: legado suportado, adapter emagrecido ou combinacao`

**Tipo**

Arquitetura / legado

**Objetivo**

Tomar a decisao bloqueante sobre o papel do `cowork-plugin` na transicao.

**Criterio de aceite**

Nao existe mais ambiguidade sobre o papel do `cowork-plugin`.

### Issue 6

**Titulo**

`Auditar cowork-plugin, runtime e docs e classificar canon vs adapter vs workaround`

**Tipo**

Analise / arquitetura

**Objetivo**

Produzir um inventario honesto do estado atual.

**Saida esperada**

Matriz com cinco classes:

1. canon
2. adapter
3. capability tecnica
4. workaround historico
5. lixo/remocao futura

### Issue 7

**Titulo**

`Mapear duplicacoes de regra entre plugin, runtime e documentacao`

**Tipo**

Arquitetura

**Objetivo**

Identificar onde a mesma regra vive em mais de um lugar e decidir qual fonte sobrevive.

## 6. Extracao do canon

### Issue 8

**Titulo**

`Extrair modulos canonicos do produto a partir do legado do plugin com inventario de sabedoria operacional`

**Tipo**

Refatoracao arquitetural

**Objetivo**

Mover para uma area canonica compartilhada os modulos que hoje vivem enterrados em `cowork-plugin`.

**Escopo inicial**

1. invocacao
2. briefing
3. persistencia
4. governanca documental
5. workflows
6. higiene / limpeza
7. disciplina conversacional herdada do plugin
8. heuristicas temporais e thresholds relevantes

### Issue 9

**Titulo**

`Consolidar templates canonicos do Workspace raiz`

**Tipo**

Produto / arquitetura

**Objetivo**

Fixar templates canonicamente controlados para:

1. `CLAUDE.md`
2. `AGENTS.md`
3. `AGENT.md` como camada de medio prazo
4. `PAUTA.md`
5. `INBOX.md`
6. `REGISTRO.md`
7. `Referencias/INDICE.md`
8. `Referencias/WORKFLOWS.md`

### Issue 10

**Titulo**

`Formalizar topologia do Workspace unico e contrato de arquivos-raiz`

**Tipo**

Produto / arquitetura

**Objetivo**

Definir a raiz unica do Prumo e o papel de cada arquivo-raiz e pasta principal.

## 7. Orquestracao, persona e contratos de host

### Issue 11

**Titulo**

`Definir contrato de orquestracao compartilhada entre hosts e runtime`

**Tipo**

Arquitetura de produto

**Objetivo**

Definir quem decide a sequencia do produto sem deixar cada host reinventar o fluxo.

**Escopo**

1. ordem de acoes
2. quando priorizar repair vs briefing vs continuacao
3. quando documentar primeiro
4. quando inbox sobe
5. como o host consome a orquestracao sem virar marionete verborrágica

### Issue 12

**Titulo**

`Definir portabilidade de persona e disciplina conversacional do Prumo`

**Tipo**

Produto / host UX

**Objetivo**

Evitar que a alma do produto evapore quando a UX voltar para o host.

**Escopo**

1. tom de voz
2. limites de listagem
3. uma pergunta por vez quando aplicavel
4. disciplina de interacao
5. persona in-prompt / adapter prompt

### Issue 13

**Titulo**

`Definir contrato de erro, fallback e graceful degradation para hosts`

**Tipo**

Arquitetura / resiliencia

**Objetivo**

Impedir que stack trace e jargao tecnico vazem para o usuario quando capacidades falham.

### Issue 14

**Titulo**

`Definir granularidade ideal das capacidades para evitar micro-tool-chaining excessivo`

**Tipo**

Runtime / host performance

**Objetivo**

Evitar que o runtime fique granular demais e obrigue hosts a encadear dezenas de chamadas para montar uma resposta simples.

## 8. Governanca documental e memoria

### Issue 15

**Titulo**

`Definir contrato de persistencia do Prumo`

**Tipo**

Produto / arquitetura

**Objetivo**

Definir o que vai para:

1. `PAUTA.md`
2. `INBOX.md`
3. `REGISTRO.md`
4. `Referencias/`
5. `Referencias/WORKFLOWS.md`
6. `_state/`

### Issue 16

**Titulo**

`Projetar governanca documental minima para a fase atual`

**Tipo**

Memoria / produto

**Objetivo**

Comecar pelo minimo que entrega valor real agora:

1. jurisdicao clara
2. nomes intuitivos
3. indices simples onde mais doer
4. gatilhos de crescimento ruim
5. limpeza segura

### Issue 17

**Titulo**

`Definir regras de limpeza automatica, assistida e delegacao otimista`

**Tipo**

Produto / memoria

**Objetivo**

Separar o que o Prumo pode reorganizar sozinho do que deve ser feito em parceria com o usuario.

**Escopo**

1. crescimento ruim de wrappers e indices de orientacao
2. crescimento ruim de `PAUTA.md`
3. listas referenciais extensas
4. contradicoes documentais
5. indices desatualizados
6. escalacao quando a mesma higiene e ignorada repetidamente
7. delegacao otimista em hosts locais fortes

### Issue 18

**Titulo**

`Especificar capacidades de memoria e governanca para o runtime em escopo proporcional`

**Tipo**

Runtime / arquitetura

**Objetivo**

Traduzir a governanca documental em capacidades concretas sem overengineering precoce.

## 9. Redesenho do runtime

### Issue 19

**Titulo**

`Inventariar comandos atuais do runtime e classificar o que e capacidade vs UX`

**Tipo**

Runtime / refatoracao

### Issue 20

**Titulo**

`Desenhar catalogo inicial de capacidades do runtime`

**Tipo**

Runtime / arquitetura

**Objetivo**

Definir o contrato inicial das capacidades centrais do runtime.

### Issue 21

**Titulo**

`Refatorar output do runtime para devolver dados e acoes, nao experiencia completa`

**Tipo**

Runtime / refatoracao

### Issue 22

**Titulo**

`Separar ativos do sistema de arquivos autorais para permitir sync seguro do core`

**Tipo**

Runtime / produto

### Issue 23

**Titulo**

`Definir politica de uso direto de arquivos locais vs wrappers do runtime`

**Tipo**

Runtime / host integration

**Objetivo**

Evitar choque de ferramentas entre hosts fortes e wrappers pesados do runtime.

### Issue 24

**Titulo**

`Definir plano de rollback e transicao segura durante a migracao capability-backend`

**Tipo**

Arquitetura / rollout

### Issue 25

**Titulo**

`Definir estrategia de teste cross-host para briefing, invocacao e documentacao`

**Tipo**

Qualidade / arquitetura

## 10. Adapters por host

### Issue 26

**Titulo**

`Especificar adapter ideal do Codex sobre runtime de capacidades`

**Tipo**

Host adapter

### Issue 27

**Titulo**

`Especificar adapter ideal do Claude sobre runtime de capacidades`

**Tipo**

Host adapter

### Issue 28

**Titulo**

`Especificar adapter ideal do Antigravity e protocolo de validacao real no host`

**Tipo**

Host adapter / validacao

**Objetivo**

Transformar Antigravity em trilho formal de validacao de experiencia e em adapter de referencia para host local forte.

### Issue 29

**Titulo**

`Especificar adapter Slack como canal corporativo sem sequestrar a UX do produto`

**Tipo**

Host adapter / comercial

## 11. Onboarding e instalacao

### Issue 30

**Titulo**

`Desenhar onboarding amigavel para instalacao da base do Prumo`

**Tipo**

Produto / UX

### Issue 31

**Titulo**

`Redesenhar instalador para habilitar hosts em linguagem humana`

**Tipo**

Produto / instalacao

### Issue 32

**Titulo**

`Separar instalacao da base do Prumo de criacao/adocao do Workspace`

**Tipo**

Produto / arquitetura

## 12. Infra de desenvolvimento multi-host

### Issue 33

**Titulo**

`Formalizar HANDOVER.md como trilho interno de coordenacao multi-host`

**Tipo**

Processo de desenvolvimento

### Issue 34

**Titulo**

`Definir protocolo de revisao cruzada entre Codex, Claude e Antigravity`

**Tipo**

Processo de desenvolvimento

### Issue 35

**Titulo**

`Atualizar README-DEV com o novo modelo de desenvolvimento multi-host`

**Tipo**

Documentacao de desenvolvimento

## 13. Ordem sugerida de abertura revisada

### Wave 1a

Checkpoint de decisoes bloqueantes. Se a Issue 5 mudar o destino do `cowork-plugin`, a Wave 1b deve ser recalibrada antes de execucao.

1. Issue 1
2. Issue 2
3. Issue 3
4. Issue 4
5. Issue 5
6. Issue 6
7. Issue 28

### Wave 1b

Design estrutural e de experiencia, ja com o destino do `cowork-plugin` definido.

1. Issue 7
2. Issue 8
3. Issue 11
4. Issue 12
5. Issue 13
6. Issue 14

### Wave 2

1. Issue 9
2. Issue 10
3. Issue 15
4. Issue 16
5. Issue 17
6. Issue 19
7. Issue 20
8. Issue 21
9. Issue 22
10. Issue 23
11. Issue 24
12. Issue 25

### Wave 3

1. Issue 18
2. Issue 26
3. Issue 27
4. Issue 29

### Wave 4

1. Issue 30
2. Issue 31
3. Issue 32
4. Issue 33
5. Issue 34
6. Issue 35

## 14. Resultado esperado deste backlog

Ao final, o repositorio deve sair de:

1. plugin legado com muita sabedoria acidental
2. runtime com ambicao demais
3. docs espalhados
4. processo multi-host implicito

Para:

1. canon explicito
2. runtime tecnico e reutilizavel
3. orquestracao compartilhada
4. persona portavel
5. hosts com UX melhor
6. memoria local governada
7. desenvolvimento multi-host documentado no GitHub
