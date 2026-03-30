# Repo, Workspace e Oficina: jurisdicao do Prumo

Status: proposta operacional imediata  
Data: 2026-03-28

## 1. O problema em uma frase

Hoje o projeto esta deixando tres coisas diferentes dividirem o mesmo quintal:

1. o **produto** que voce desenvolve
2. o **workspace** que voce usa como usuario
3. a **oficina** onde Codex, Claude e Antigravity se coordenam

Enquanto isso continuar borrado, o sistema vai contaminar o produto com backstage e contaminar o backstage com vida real do usuario.

## 2. Regra rapida

Se a conversa for sobre **desenvolver o produto**, a janela do Codex deve abrir em:

`/Users/tharsovieira/Documents/DailyLife/Prumo`

Se a conversa for sobre **usar o Prumo como usuario**, operar pauta, inbox, registro, referencias ou contexto vivo, a janela deve abrir em:

`/Users/tharsovieira/Documents/DailyLife`

Se a tarefa cruzar as duas coisas, a regra e:

1. abrir no repo do produto
2. declarar explicitamente que vai tocar o workspace vivo
3. tratar qualquer mudanca em `DailyLife/` como mudanca de instancia de usuario, nao como mudanca de codigo do produto

Em portugues simples: **`Prumo/` e bancada. `DailyLife/` e casa habitada.**

## 2.1 Regra de nomenclatura que passa a valer

Para reduzir erro operacional de agente sem contexto suficiente:

1. **`_state/` fica reservado ao workspace vivo do usuario**
2. **a oficina de desenvolvimento do repo nao deve mais ser chamada de `_state/`**
3. o nome-alvo da oficina passa a ser **`.workbench/`**

Traduzindo:

1. `DailyLife/_state/` continua sendo estado vivo do usuario
2. `Prumo/_state/` era o nome legado e transitorio da oficina
3. o nome correto, daqui para frente, para a camada de oficina e `.workbench/`

## 3. Os tres territorios

## 3.1 Repositorio do produto

Path:

`/Users/tharsovieira/Documents/DailyLife/Prumo`

Aqui mora o que e fonte de verdade de desenvolvimento:

1. codigo
2. runtime
3. plugin/adapters
4. scripts
5. ADRs
6. backlog
7. specs
8. testes
9. templates canonicos
10. documentacao de arquitetura e desenvolvimento

Isso **deve** ir para o GitHub.

## 3.2 Workspace do usuario

Path:

`/Users/tharsovieira/Documents/DailyLife`

Aqui mora a vida real do usuario.

Arquivos e areas que hoje pertencem claramente a esse territorio:

1. [AGENTS.md](/Users/tharsovieira/Documents/DailyLife/AGENTS.md)
2. [CLAUDE.md](/Users/tharsovieira/Documents/DailyLife/CLAUDE.md)
3. [INBOX.md](/Users/tharsovieira/Documents/DailyLife/INBOX.md)
4. [PAUTA.md](/Users/tharsovieira/Documents/DailyLife/PAUTA.md)
5. [REGISTRO.md](/Users/tharsovieira/Documents/DailyLife/REGISTRO.md)
6. [PRUMO-CORE.md](/Users/tharsovieira/Documents/DailyLife/PRUMO-CORE.md)
7. [Referencias](/Users/tharsovieira/Documents/DailyLife/Referencias)
8. [_state](/Users/tharsovieira/Documents/DailyLife/_state)
9. pastas tematicas como [Pessoal](/Users/tharsovieira/Documents/DailyLife/Pessoal), [Profissional](/Users/tharsovieira/Documents/DailyLife/Profissional), [Projetos](/Users/tharsovieira/Documents/DailyLife/Projetos)

Isso **nao deve** ir para o GitHub do produto por padrao.

O GitHub do produto pode guardar:

1. templates vazios
2. exemplos sanitizados
3. schemas
4. contratos de persistencia

Mas nao os dados vivos do usuario.

## 3.2.1 Jurisdicao interna do workspace

Dentro do workspace do usuario tambem precisa haver fronteira. Deixar tudo na raiz foi util como etapa bruta de transicao, mas em UX isso parece mudanca feita com as caixas ainda no corredor.

A topologia alvo passa a ser:

1. **raiz minima** para `AGENT.md`, `AGENTS.md` e `CLAUDE.md`
2. **`Prumo/`** para memoria viva do usuario
3. **`/.prumo/`** para estado tecnico e assets atualizaveis do sistema

O detalhamento dessa planta fica em [WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md).

Regra seca:

1. raiz nao e almoxarifado
2. `/Prumo/` nao e lugar para update meter a mao sem pedir licenca
3. `/.prumo/` nao e lugar para memoria autoral do usuario

## 3.3 Oficina de desenvolvimento

Esta e a camada que mais gerou confusao.

Hoje ela aparece, por exemplo, em:

1. [Prumo/.workbench/HANDOVER.md](/Users/tharsovieira/Documents/DailyLife/Prumo/.workbench/HANDOVER.md)
2. [Prumo/.workbench/LESSONS_LEARNED.md](/Users/tharsovieira/Documents/DailyLife/Prumo/.workbench/LESSONS_LEARNED.md)
3. [Prumo/.workbench/REVIEW-2026-03-25.md](/Users/tharsovieira/Documents/DailyLife/Prumo/.workbench/REVIEW-2026-03-25.md)
4. [Prumo/.workbench/REVIEW-ANTIGRAVITY-2026-03-27.md](/Users/tharsovieira/Documents/DailyLife/Prumo/.workbench/REVIEW-ANTIGRAVITY-2026-03-27.md)
5. [Prumo/.workbench/validation-claude-issue20.md](/Users/tharsovieira/Documents/DailyLife/Prumo/.workbench/validation-claude-issue20.md)

Isso **nao e produto** e **nao e workspace do usuario**.

Isso e oficina:

1. handovers
2. revisoes cruzadas
3. licoes aprendidas da implementacao
4. notas internas entre agentes

Esses artefatos nao devem contaminar o produto final nem a experiencia do usuario.

## 4. Politica de versionamento

## 4.1 Vai para o GitHub do produto

1. codigo fonte
2. runtime
3. adapters
4. scripts de instalacao e manutencao
5. ADRs
6. backlog de implementacao
7. specs
8. stories
9. templates canonicos do workspace
10. schemas e contratos
11. exemplos sanitizados
12. documentacao tecnica e de desenvolvimento
13. drafts de issue como [github-issues](/Users/tharsovieira/Documents/DailyLife/Prumo/github-issues)

## 4.2 Nao vai para o GitHub do produto

1. `HANDOVER.md`
2. reviews internas de agentes
3. licoes aprendidas de oficina em estado bruto
4. `_state/` vivo do workspace do usuario
5. `PAUTA.md` real
6. `INBOX.md` real
7. `REGISTRO.md` real
8. referencias reais e documentos pessoais
9. qualquer dado operacional vivo do usuario

## 4.3 Pode ir para o GitHub em forma sanitizada

1. exemplos de `AGENT.md`
2. exemplo de estrutura de `_state/`
3. template de `PAUTA.md`
4. template de `REGISTRO.md`
5. snapshots ficticios
6. fixtures de teste

Em outras palavras:

1. o GitHub guarda a planta
2. o usuario guarda a casa habitada
3. a oficina guarda os rabiscos de obra

## 5. Classificacao do que existe hoje

## 5.1 Coisas claramente do produto

1. [runtime](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime)
2. [cowork-plugin](/Users/tharsovieira/Documents/DailyLife/Prumo/cowork-plugin)
3. [scripts](/Users/tharsovieira/Documents/DailyLife/Prumo/scripts)
4. [skills](/Users/tharsovieira/Documents/DailyLife/Prumo/skills)
5. [ADR-001-GOOGLE-INTEGRATION.md](/Users/tharsovieira/Documents/DailyLife/Prumo/ADR-001-GOOGLE-INTEGRATION.md)
6. [PRUMO-CAPABILITY-BACKEND-ARCHITECTURE.md](/Users/tharsovieira/Documents/DailyLife/Prumo/PRUMO-CAPABILITY-BACKEND-ARCHITECTURE.md)
7. [GITHUB-ISSUE-BACKLOG-CAPABILITY-BACKEND.md](/Users/tharsovieira/Documents/DailyLife/Prumo/GITHUB-ISSUE-BACKLOG-CAPABILITY-BACKEND.md)
8. [github-issues](/Users/tharsovieira/Documents/DailyLife/Prumo/github-issues)

## 5.2 Coisas claramente de oficina

1. [Prumo/.workbench](/Users/tharsovieira/Documents/DailyLife/Prumo/.workbench)

Diagnostico direto:

O nome `_state` aqui e ruim. Ele sugere estado do sistema, quando na pratica e estado da oficina.

Recomendacao:

Reservar `_state/` exclusivamente para o workspace do usuario e renomear esta area do repo para:

1. `.workbench/`

Porque deixa obvio que:

1. e interno
2. e de desenvolvimento
3. nao e parte da instancia do usuario
4. nao e pasta canonica do produto

## 5.3 Coisas claramente do workspace do usuario

Tudo que esta na raiz de `DailyLife/` e faz o Prumo funcionar como sistema vivo para voce:

1. wrappers e arquivos-raiz
2. referencias
3. pauta
4. inbox
5. registro
6. contexto tematico
7. `_state/` do usuario

## 5.4 Coisas mal nomeadas ou frouxas demais

### `docs/`

Hoje [docs](/Users/tharsovieira/Documents/DailyLife/Prumo/docs) contem pelo menos:

1. [bridges/google-apps-script/apps-script-setup.md](/Users/tharsovieira/Documents/DailyLife/Prumo/bridges/google-apps-script/apps-script-setup.md)
2. [bridges/google-apps-script](/Users/tharsovieira/Documents/DailyLife/Prumo/bridges/google-apps-script)
3. [docs/stories/us-001-antigravity-adapter.md](/Users/tharsovieira/Documents/DailyLife/Prumo/docs/stories/us-001-antigravity-adapter.md)

Ou seja: `docs/` esta funcionando como gaveta chamada "diversos".

Recomendacao:

Fatiar por papel:

1. `docs/dev/` para documentacao de desenvolvimento
2. `docs/integrations/` para setup tecnico replicavel
3. `stories/` ou `product-stories/` para historias estruturadas
4. `workspace-template/` para o que deve ser copiado ou gerado no workspace do usuario

## 6. Regra operacional para abrir janelas no Codex

## Caso A: conversa sobre desenvolver o produto

Abra em:

`/Users/tharsovieira/Documents/DailyLife/Prumo`

Exemplos:

1. arquitetura
2. refatoracao
3. backlog
4. adapters
5. runtime
6. plugin
7. testes do produto
8. docs de desenvolvimento
9. abrir issues

## Caso B: conversa sobre usar o Prumo como usuario

Abra em:

`/Users/tharsovieira/Documents/DailyLife`

Exemplos:

1. "Prumo"
2. briefing do dia
3. organizar pauta
4. recuperar referencia
5. atualizar registro
6. mexer em contexto vivo
7. manutencao do workspace real

## Caso C: tarefa de fronteira

Abra em:

`/Users/tharsovieira/Documents/DailyLife/Prumo`

Mas declare explicitamente no inicio algo como:

"Esta tarefa vai alterar o produto e tambem tocar o workspace vivo em `DailyLife/` para validar a integracao."

Sem essa declaracao, o default deve ser **nao tocar** o workspace real do usuario.

## 7. Decisoes praticas imediatas

## 7.1 Decisao 1

Para conversas de desenvolvimento no Codex, o cwd padrao deve ser:

`/Users/tharsovieira/Documents/DailyLife/Prumo`

Nao `DailyLife/`.

Essa e a resposta curta para a sua duvida.

## 7.2 Decisao 2

`DailyLife/` deve ser tratado como **instancia viva de usuario**, nao como repo do produto.

## 7.3 Decisao 3

`.workbench/` deve ser entendido como **oficina interna** do repo.

Daqui para frente, a regra e:

1. `_state/` = estado vivo do usuario
2. `.workbench/` = backstage de desenvolvimento

Se um documento do repo falar em `_state/` no contexto da oficina, ele esta usando nome legado e precisa ser corrigido.

## 7.4 Decisao 4

O repo precisa ganhar uma area canonicamente nomeada para templates do workspace.

Sugestao:

`workspace-template/`

Para guardar:

1. template de `AGENT.md`
2. template de `CLAUDE.md`
3. template de `AGENTS.md`
4. template de `PAUTA.md`
5. template de `INBOX.md`
6. template de `REGISTRO.md`
7. estrutura esperada de `_state/`

## 7.5 Decisao 5

`docs/` deve ser reorganizado por papel. Do jeito atual, ele e um nome amplo demais para um projeto que ja esta precisando de cerca eletrica semantica.

## 8. O que isso evita

1. handover vazando para o produto
2. arquivo do usuario virando fixture sem querer
3. backlog tecnico sendo confundido com memoria do sistema
4. conversa de desenvolvimento alterando pauta viva
5. conversa de usuario mexendo em codigo do produto

## 9. Formula final

Se a pergunta for:

"Estou falando com o Codex como dev ou como usuario?"

use esta resposta:

1. **dev**: abrir em [Prumo](/Users/tharsovieira/Documents/DailyLife/Prumo)
2. **usuario**: abrir em [DailyLife](/Users/tharsovieira/Documents/DailyLife)

Se a tarefa misturar os dois papeis, trate isso como excecao explicita e perigosa, nao como estado natural das coisas.

O galinheiro so fica em ordem quando a cozinha para de compartilhar armario com a oficina.
