# Plano de implementacao: adapters de host do Prumo

Status: plano operacional do bloco seguinte

Relacionado:

1. [LOCAL-RUNTIME-TRANSITION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/LOCAL-RUNTIME-TRANSITION-PLAN.md)
2. [LOCAL-RUNTIME-PHASE1-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/LOCAL-RUNTIME-PHASE1-PLAN.md)
3. [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md)
4. Issue pública da Fase 1: [#41](https://github.com/tharso/prumo/issues/41)

## 1. Por que este plano existe

Porque já ficou claro demais que "host" e "modelo" não são a mesma coisa.

Se tratarmos:

1. `Cowork` e `Claude Code` como uma coisa só porque ambos orbitam o universo Claude;
2. `Gemini CLI` e `Antigravity` como uma coisa só porque ambos orbitam o universo Gemini;

vamos enfiar a cabeça num balde metodológico e chamar isso de abstração.

O que muda o adapter do Prumo não é o sobrenome do modelo. É a superfície real do host:

1. como ele invoca;
2. se ele tem shell local;
3. se ele tem acesso a arquivos locais;
4. como lida com permissões por app;
5. quais affordances ele expõe (`/prumo`, prompt livre, command palette, tool call, skill, bridge, JSON etc.).

Em português simples: mesma família de cérebro não significa mesma porta, mesma maçaneta, nem mesma fechadura.

## 2. Taxonomia correta

Para o Prumo, precisamos separar duas camadas:

### 2.1. Família de modelo / provedor

Exemplos:

1. Anthropic / Claude
2. OpenAI / Codex
3. Google / Gemini

Isso importa para:

1. disponibilidade de modelos;
2. personalidade da interface;
3. algumas integrações de produto.

Mas isso nao define adapter.

### 2.2. Host / superfície de execução

Exemplos:

1. `Cowork`
2. `Claude Code`
3. `Codex`
4. `Gemini CLI`
5. `Antigravity`

Isso sim define adapter.

Porque adapter precisa saber:

1. como o usuário chama o Prumo;
2. como o host executa `prumo`;
3. como o host consome `prumo start --format json`;
4. como permissões locais se comportam naquele app.

## 3. Premissas de trabalho

Estas premissas ficam explícitas para ninguém voltar a escorregar:

1. `Cowork` e `Claude Code` são hosts diferentes e merecem adapters diferentes, mesmo quando usarem a mesma família Claude.
2. `Gemini CLI` e `Antigravity` são hosts diferentes e merecem adapters diferentes, mesmo quando usarem a mesma família Gemini.
3. `Codex` é host próprio e não deve ser tratado como benchmark universal. Ele é só o primeiro trilho de implementação porque já mostrou o comportamento mais promissor.
4. A ordem de implementação não define host favorito. Define apenas por onde começamos a asfaltar a estrada.
5. Permissões locais são por app. `Codex.app` autorizado para Apple Reminders não implica `Cowork.app` ou `Antigravity.app` autorizados.

## 3.1. Mapa de documentação oficial por host

Antes de codar adapter, vale fixar onde a documentação oficial realmente existe e onde ela começa a rarear.

### Codex

Fontes oficiais relevantes:

1. OpenAI Codex docs: [developers.openai.com/codex/cloud](https://developers.openai.com/codex/cloud)
2. OpenAI local shell tool: [developers.openai.com/api/docs/guides/tools-local-shell](https://developers.openai.com/api/docs/guides/tools-local-shell)
3. Repositório oficial do Codex CLI: [github.com/openai/codex](https://github.com/openai/codex)

O que essas fontes deixam claro:

1. Codex é um agente de código que lê, edita e executa código.
2. O CLI roda localmente na máquina do usuário.
3. O ecossistema oficial aceita contexto por arquivo (`AGENTS.md`) e inclui superfície local/IDE/app.

O que isso implica para o adapter:

1. `Codex` é candidato natural ao primeiro slice porque a documentação oficial já assume operação local real.
2. O adapter não precisa inventar teoria para shell local. A própria documentação já vive nesse terreno.

### Claude Code

Fontes oficiais relevantes:

1. Overview: [code.claude.com/docs/en/overview](https://code.claude.com/docs/en/overview)
2. CLI reference: [code.claude.com/docs/en/cli-reference](https://code.claude.com/docs/en/cli-reference)
3. Plugins reference: [code.claude.com/docs/en/plugins-reference](https://code.claude.com/docs/en/plugins-reference)
4. Skills: [code.claude.com/docs/en/slash-commands](https://code.claude.com/docs/en/slash-commands)

O que essas fontes deixam claro:

1. Claude Code existe em múltiplas superfícies: terminal, IDE, desktop app e web.
2. O terminal/CLI é first-class.
3. O sistema de plugins, skills, agents, hooks e MCP é formal e bem documentado.

O que isso implica para o adapter:

1. `Claude Code` merece adapter próprio.
2. Não devemos tratá-lo como sinônimo de `Cowork`.
3. O terreno documental aqui é mais sólido do que no Cowork.

### Cowork

Fontes oficiais relevantes:

1. O melhor chão oficial público disponível hoje continua sendo a documentação do ecossistema Claude Code acima.
2. Para comportamento operacional específico do Cowork neste projeto, ainda dependemos do playbook local: [COWORK-MARKETPLACE-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/COWORK-MARKETPLACE-PLAYBOOK.md)

O que está claro:

1. A família Claude tem documentação oficial robusta para CLI, plugins e desktop app.
2. O comportamento específico do `Cowork` como casca de plugin/store/skill registry continua menos documentado publicamente do que seria saudável.

O que isso implica para o adapter:

1. O adapter de `Cowork` precisa ser guiado por teste real e pelo nosso playbook, não só por docs oficiais.
2. Não convém vender abstração onde a própria documentação pública ainda não fecha o circuito.

### Gemini CLI

Fontes oficiais relevantes:

1. Google for Developers summary: [developers.google.com/gemini-code-assist/docs/gemini-cli](https://developers.google.com/gemini-code-assist/docs/gemini-cli)
2. Repositório oficial: [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)

O que essas fontes deixam claro:

1. Gemini CLI é um agente open source de terminal.
2. Ele usa ferramentas embutidas, shell local, operações de arquivo, MCP e saídas estruturadas.
3. O Google o trata como peça canônica do ecossistema Gemini Code Assist.

O que isso implica para o adapter:

1. `Gemini CLI` pode ser trabalhado com a mesma lógica de adapter fino usada em `Codex`, mas não por copiar e colar contrato no escuro.
2. A documentação já sinaliza shell, arquivos, MCP e JSON. Isso reduz a necessidade de arqueologia por tentativa e erro.

### Antigravity

Fontes oficiais relevantes:

1. Codelab oficial: [codelabs.developers.google.com/getting-started-google-antigravity](https://codelabs.developers.google.com/getting-started-google-antigravity)
2. Blog do Google sobre Gemini 3 / Antigravity: [blog.google/intl/en-mena/product-updates/explore-get-answers/gemini-3-launches-in-mena/](https://blog.google/intl/en-mena/product-updates/explore-get-answers/gemini-3-launches-in-mena/)

Observação importante:

1. o codelab aponta para `antigravity.google` e `antigravity.google/docs` como destinos oficiais;
2. nesta sessão, esses endpoints não entregaram conteúdo utilizável;
3. então a base oficial concreta acessível aqui ficou no codelab e no blog do Google.

O que essas fontes deixam claro:

1. Antigravity é host agent-first, não mero wrapper de chat.
2. Ele tem acesso ao editor, terminal e browser.
3. Ele trabalha com workspaces locais.
4. Permissões e autonomia são por política do app, inclusive para terminal e browser.
5. Ele possui regras, workflows e skills próprios no workspace.

O que isso implica para o adapter:

1. `Antigravity` não deve ser tratado como `Gemini CLI com UI`.
2. O adapter dele terá de respeitar uma superfície própria: Manager View, Editor View, browser agent, políticas de autonomia e arquivos `.agents/...`.

## 3.2. Conclusão da pesquisa documental

Depois de levantar a documentação oficial, a situação fica assim:

1. `Codex`: terreno oficial forte para operação local.
2. `Claude Code`: terreno oficial forte para CLI, plugins, skills e múltiplas superfícies.
3. `Cowork`: terreno oficial parcial; operação real ainda depende mais de teste de campo e playbook local.
4. `Gemini CLI`: terreno oficial forte para terminal, shell, MCP e saída estruturada.
5. `Antigravity`: terreno oficial suficiente para provar que é outro host, mas ainda menos confortável do que Gemini CLI em documentação acessível.

Em português simples: a documentação oficial já basta para impedir a confusão conceitual. Mas não basta, sozinha, para nos poupar de teste real em `Cowork` e `Antigravity`.

## 4. Objetivo deste bloco

Depois da Fase 1, o objetivo muda de natureza.

Nao estamos mais tentando provar que o runtime existe.

Estamos tentando provar que o usuário consegue:

1. abrir o host de preferência;
2. chamar o Prumo de forma curta;
3. ter o host encaminhando isso para o runtime;
4. receber uma experiência coerente sem precisar saber que existe `prumo start`.

Em outras palavras: o próximo bloco é `Invocation UX` materializada por host.

## 5. Contrato canônico que todos os adapters devem respeitar

Todos os adapters partem do mesmo núcleo:

1. porta curta técnica:
   - `prumo`
   - `prumo start`
2. briefing explícito:
   - `prumo briefing --workspace . --refresh-snapshot`
3. resposta estruturada:
   - `prumo start --format json`

Campos importantes do JSON:

1. `kind = shell` -> executar `shell_command`
2. `kind = host-prompt` -> usar `host_prompt` como continuação guiada
3. `adapter_contract_version` -> saber se o adapter já entende o contrato atual ou se está lendo jornal velho
4. `workspace_resolution` -> saber se o runtime inferiu o workspace ou recebeu caminho explícito
5. `adapter_hints` -> parar de adivinhar entrada curta, briefing explícito e rota estruturada

O adapter não deve:

1. reinterpretar setup;
2. reinterpretar migrate;
3. inventar heurística paralela para auth/repair;
4. rodar briefing por reflexo só porque não sabe o que fazer.

## 6. Ordem de implementação

Esta é ordem de implementação. Não é ranking de produto.

### 6.1. Slice 1: Codex

Motivo:

1. já mostrou, em teste real, que responde a `Prumo` de forma muito próxima do comportamento desejado;
2. tem shell local;
3. lê os wrappers do workspace;
4. reduz atrito para validar adapter fino sem depender do circo de plugin do Cowork.

Playbook operacional:

1. [CODEX-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CODEX-ADAPTER-PLAYBOOK.md)

Objetivo:

1. consolidar `Codex` como primeiro adapter implementado;
2. validar que `Prumo` vira `prumo`;
3. validar que `briefing explícito` vira `prumo briefing`;
4. validar consumo de `start --format json` quando fizer sentido.

### 6.2. Slice 2: Claude Code

Motivo:

1. pertence à família Claude, mas não carrega o mesmo teatro de plugin do Cowork;
2. ajuda a testar se a lógica da família Claude ainda se comporta quando a superfície muda;
3. impede que `Cowork` vire sinônimo mental de "host Claude".

Playbook operacional:

1. [CLAUDE-CODE-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CLAUDE-CODE-ADAPTER-PLAYBOOK.md)

Objetivo:

1. provar que a diferença relevante é host, não sobrenome do modelo;
2. validar invocação curta e acesso local em outro ambiente Claude.

Estado atual:

1. shell explícito validado;
2. `start --format json` validado;
3. invocação curta ainda fora do trilho;
4. `Apple Reminders` bloqueado por limitação operacional de TCC/app no host.

### 6.3. Slice 3: Cowork

Motivo:

1. continua importante para usuários reais;
2. já mostrou que funciona como casca fina quando executa `prumo`;
3. continua instável quando tenta agir como ecossistema nativo de plugin/skill.

Objetivo:

1. manter o Cowork no papel de adapter fino;
2. evitar reabrir o romance tóxico com plugin como motor;
3. se `/prumo` existir, ele deve bater em `start` e não inventar outro Prumo dentro do host.

Playbook operacional:

1. [COWORK-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/COWORK-ADAPTER-PLAYBOOK.md)
2. [COWORK-MARKETPLACE-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/COWORK-MARKETPLACE-PLAYBOOK.md)

Estado atual:

1. `shell-thin` validado;
2. invocação curta/nativa falhou;
3. o host voltou a plugin/skill/fluxo legado quando recebeu `Prumo`;
4. houve leitura de arquivo e escrita de `briefing-state.json` fora do runtime;
5. o problema aqui não é falta de comando, e sim falta de disciplina de adapter.

### 6.4. Slice 4: Gemini CLI

Motivo:

1. permite validar a mesma tese num host de outra família;
2. shell local tende a deixar o teste mais limpo.

Objetivo:

1. provar que a arquitetura é de fato host-agnostic;
2. validar paridade mínima do contrato em outro ecossistema.

Playbook operacional:

1. [GEMINI-CLI-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/GEMINI-CLI-ADAPTER-PLAYBOOK.md)

Estado atual:

1. invocação curta falhou;
2. briefing explícito falhou;
3. `start --format json` falhou;
4. o host improvisou runtime e chegou a escrever estado sem passar pelo comando.

### 6.5. Slice 5: Antigravity

Motivo:

1. expõe outra superfície dentro do universo Gemini;
2. força a disciplina de não confundir família de modelo com adapter reaproveitável.

Objetivo:

1. validar o par `Gemini CLI` versus `Antigravity` como hosts distintos;
2. garantir que a taxonomia deste plano não era só discurso bonito.

Playbook operacional:

1. [ANTIGRAVITY-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/ANTIGRAVITY-ADAPTER-PLAYBOOK.md)

Estado atual:

1. invocação curta passou;
2. briefing explícito passou;
3. `start --format json` passou;
4. o host respeitou o runtime, sem improvisar briefing por leitura de arquivo nem escrever `_state/` na unha;
5. ainda tropeça em disciplina de execução (comando extra e repetição de flag inválida);
6. `Apple Reminders` segue pendente por permissão por app.

## 7. Critério de aceite por host

Um host será considerado "no trilho" quando:

1. o usuário puder chamar `Prumo` de forma curta;
2. o host encaminhar isso para `prumo start` ou `prumo`;
3. o host não improvisar briefing por conta própria;
4. o host conseguir executar `prumo briefing --workspace . --refresh-snapshot` quando o pedido for explícito;
5. quando consumir JSON, respeitar `kind`, `shell_command` e `host_prompt`;
6. quando consumir JSON, também ler `adapter_contract_version`, `workspace_resolution` e `adapter_hints` em vez de improvisar.

Um host não será considerado pronto só porque:

1. roda um comando no terminal quando alguém dita a linha completa;
2. parece funcionar no caminho feliz;
3. compartilha a mesma família de modelo com outro host.

## 8. Matriz mínima de adapter

### 8.1. Codex

Porta curta desejada:

1. `Prumo`

Bridge esperado:

1. `Prumo` -> `prumo`
2. pedido de briefing explícito -> `prumo briefing --workspace . --refresh-snapshot`

Risco principal:

1. o host acertar por boa vontade em vez de contrato.

### 8.2. Claude Code

Porta curta desejada:

1. `Prumo`

Bridge esperado:

1. igual ao Codex, mas validado como host distinto

Risco principal:

1. tratarmos "Claude" como categoria única e deixarmos Cowork contaminar a leitura.

### 8.3. Cowork

Porta curta desejada:

1. `/prumo`
2. ou instrução textual equivalente que execute `prumo`

Bridge esperado:

1. `/prumo` -> `start`
2. `/briefing` ou `/prumo:briefing` -> `briefing`

Risco principal:

1. plugin/skill registry velho voltar a sequestrar a UX.

Status de campo:

1. bom como casca fina de shell;
2. ruim como rota curta/nativa neste momento.

### 8.4. Gemini CLI

Porta curta desejada:

1. `Prumo`

Bridge esperado:

1. igual ao Codex no nível de contrato

Risco principal:

1. assumir que comportamento bom em Codex se transfere automaticamente.

### 8.5. Antigravity

Porta curta desejada:

1. `Prumo`
2. affordance equivalente da interface, se houver

Bridge esperado:

1. mesmo contrato do Gemini CLI;
2. implementação própria por ser outro host.

Risco principal:

1. permissões por app e affordances diferentes serem tratadas como detalhe irrelevante.

Status de campo:

1. melhor comportado do que o `Gemini CLI`;
2. ainda não disciplinado o bastante para nota máxima.

### 8.6. Fotografia atual dos hosts

1. `Codex` -> aprovado como primeiro adapter implementado.
2. `Claude Code` -> shell explícito aprovado; invocação curta e `Apple Reminders` ainda pendentes.
3. `Cowork` -> serve como casca fina quando executa `prumo`; invocação curta/nativa falhou e o ecossistema plugin-first continua pouco confiável.
4. `Gemini CLI` -> reprovado como adapter nesta rodada.
5. `Antigravity` -> validado para rota curta e uso do runtime; `Apple Reminders` ainda pendente por permissão por app e a disciplina operacional ainda merece vigilância.

## 9. Entregáveis deste novo bloco

1. este plano operacional;
2. documentação explícita da taxonomia `família != host`;
3. adapter `Codex` como primeiro implementado;
4. adapter `Claude Code` como segundo corte;
5. critérios de aceite do `Cowork` como adapter fino;
6. backlog explícito para `Gemini CLI` e `Antigravity`.

## 10. O que não fazer agora

1. não reabrir batalha filosófica sobre plugin;
2. não chamar nenhum host de "prioritário" no produto;
3. não assumir paridade automática entre hosts da mesma família;
4. não empilhar integração nova antes de fechar a invocação;
5. não tentar implementar cinco adapters ao mesmo tempo e chamar isso de estratégia.

## 11. Próxima ação recomendada

A próxima ação recomendada é:

1. consolidar `Codex` como primeiro adapter implementado;
2. testar e documentar `Claude Code` como host distinto de `Cowork`;
3. só depois encostar de novo no `Cowork` como adapter fino;
4. deixar `Gemini CLI` e `Antigravity` como próximos slices claros, não como promessa nebulosa.
5. tratar `Antigravity` como host mais promissor do lado Gemini do que o `Gemini CLI`, sem transformar isso em atestado de maturidade precoce.
6. manter `Cowork` oficialmente na categoria `shell-thin` até a invocação curta provar que consegue andar sem muleta de plugin.

Se isso não ficar explícito agora, o projeto volta a confundir ecossistema de marca com superfície de execução. E isso seria como escolher marceneiro pela cor do caminhão.
