# Arquitetura proposta: Prumo como backend de capacidades com experiencia multi-host

Status: proposta arquitetural

Data: 2026-03-27

Relacionado:

1. [README.md](/Users/tharsovieira/Documents/DailyLife/Prumo/README.md)
2. [ADR-001-GOOGLE-INTEGRATION.md](/Users/tharsovieira/Documents/DailyLife/Prumo/ADR-001-GOOGLE-INTEGRATION.md)
3. [HOST-ADAPTER-IMPLEMENTATION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/HOST-ADAPTER-IMPLEMENTATION-PLAN.md)
4. [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md)
5. [PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md](/Users/tharsovieira/Documents/DailyLife/Prumo/PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md)

## 1. Por que este documento existe

Porque o Prumo entrou num ponto de bifurcacao perigoso.

De um lado, a linha `plugin + skills` preserva melhor a fluidez do produto: conversa boa, interacao viva, leitura do contexto, continuidade mais natural.

Do outro, a linha `runtime-first` resolveu problemas reais de estrutura, agnosticismo e integracao, mas corre o risco de transformar o Prumo num despachante de comandos com bons modos e pouca alma.

O objetivo deste documento e resolver essa tensao sem cair em romantizacao do passado nem em fetiche por infraestrutura.

Em portugues simples:

1. o Prumo nao deve voltar a depender de um host unico;
2. o Prumo nao deve sacrificar a qualidade da experiencia para parecer mais “agnostico” no papel;
3. o runtime nao deve disputar o papel de protagonista conversacional;
4. plugins, skills e adapters devem voltar a ser frente de experiencia;
5. a fonte de verdade do sistema precisa continuar una.

## 2. Diagnostico

### 2.1. O que a linha plugin fazia bem

1. mantinha uma experiencia mais fluida;
2. deixava o agente interagir com os assuntos e nao apenas enumerar tarefas;
3. preservava melhor a sensacao de operador inteligente;
4. escondia mais infraestrutura e mostrava mais produto.

### 2.2. O que motivou a migracao

1. reduzir dependencia de um host especifico;
2. evitar acoplamento comercial a um plano ou plataforma unica;
3. ganhar controle sobre integracoes, estado, automacoes e atualizacoes;
4. permitir multiplos hosts sobre a mesma base do produto.

### 2.3. O problema da fase atual

O movimento em direcao ao runtime resolveu parte da mecanica, mas contaminou a experiencia.

O risco hoje e este:

1. o runtime querer ser infraestrutura;
2. o runtime querer ser experiencia;
3. o runtime querer ser a principal porta de entrada;
4. o produto passar a soar como “menu de operacoes” em vez de operador inteligente.

Se isso continuar, o Prumo pode ficar mais robusto por baixo e menos desejavel por cima. E isso, para produto, e um pessimo negocio.

## 3. Tese desta arquitetura

O Prumo deve ser redesenhado assim:

1. **host-native na experiencia**
2. **local-first na memoria**
3. **runtime-first nas capacidades tecnicas**
4. **orquestracao compartilhada, nao improvisada por host**
5. **single source of truth no sistema**
6. **governanca documental como subsistema central**

Traduzindo:

1. a conversa e a fluidez moram no host;
2. a persistencia e o contexto moram em arquivos locais;
3. integracoes, automacoes, indices e operacoes confiaveis moram no runtime;
4. a sequencia do produto nao pode ser reinventada por cada host;
5. nenhum host deve inventar seu proprio Prumo;
6. organizacao, catalogacao e limpeza nao sao detalhe. Sao parte do produto.

### 3.1. Corte pratico para Google no MVP

Para Gmail, Calendar e Drive, o MVP nao precisa que o runtime vire dono da coleta quando os hosts principais ja oferecem conectores oficiais/MCP decentes.

A regra pratica fica assim:

1. o host coleta;
2. o Prumo interpreta, organiza e registra;
3. o runtime so entra quando houver motivo real de fallback, automacao sem sessao ou host sem conector.

Em outras palavras: no MVP, o Prumo consome Google. Nao precisa possuir Google.

## 4. O que significa “runtime como backend de capacidades”

Significa que o runtime para de tentar ser:

1. o narrador principal do Prumo;
2. o autor da UX do briefing;
3. o companheiro conversacional principal;
4. o lugar onde nasce a personalidade do produto.

E passa a ser:

1. executor de integracoes;
2. provedor de dados e acoes;
3. operador de automacoes;
4. guardiao de estado tecnico;
5. backend de memoria estrutural, catalogacao e governanca;
6. infraestrutura compartilhada por qualquer host.

Mas isso sozinho nao resolve o problema principal.

Se o runtime so expuser capacidades granulares e cada host decidir:

1. quando chamar;
2. em que ordem chamar;
3. como combinar os retornos;
4. quando documentar;
5. como reagir a erro;

entao a inteligencia real do produto volta a se espalhar pelos adapters.

Por isso, capability-backend sem orquestracao compartilhada e so descentralizacao bonita com esquizofrenia adiada.

Em vez de devolver “o briefing inteiro com voz e estilo”, o runtime deve expor capacidades como:

1. `workspace.setup`
2. `workspace.repair`
3. `workspace.migrate`
4. `workspace.context_dump`
5. `briefing.snapshot_refresh`
6. `briefing.get_structured_context`
7. `inbox.preview`
8. `google.auth`
9. `google.calendar_summary`
10. `google.email_triage`
11. `memory.catalog_scan`
12. `memory.rebuild_indices`
13. `memory.detect_drift`
14. `memory.propose_cleanup`
15. `handover.list`
16. `handover.register`
17. `core.sync_assets`

O host conversa. O runtime faz trabalho pesado.

Essa frase precisa de complemento:

1. o host conversa;
2. o runtime executa;
3. a orquestracao do produto precisa ser compartilhada e explicitamente contratada.

Sem isso, cada host vira diretor de cena do proprio Prumo.

## 4.1. A camada que faltava: orquestracao compartilhada

Entre host e runtime precisa existir uma camada logica de orquestracao.

Ela nao e:

1. um host especifico;
2. um CLI cheio de prosa;
3. uma reimplementacao completa do produto em Python;
4. um monte de hints frouxos sem autoridade.

Ela deve ser:

1. um contrato de sequencia consumivel por hosts;
2. uma politica comum para decidir proximo movimento;
3. uma definicao compartilhada de fallback e erro;
4. um lugar onde a sabedoria operacional do produto mora sem ficar refem do host.

Exemplos do que essa camada precisa decidir:

1. quando `repair` precede briefing;
2. quando o produto deve continuar algo quente em vez de abrir panorama;
3. quando inbox vira prioridade;
4. quando documentar primeiro e quando executar primeiro;
5. o que fazer quando uma capacidade falha;
6. que grau de detalhe o host precisa receber para manter fluidez sem micro-tool-chaining excessivo.

Em portugues simples: host nao pode ser obrigado a improvisar roteiro com um monte de pedaco de dado solto.

## 5. Principio central de experiencia

O produto que o usuario compra nao e “um runtime agnostico”.

O produto que o usuario percebe e:

1. alguem que lembra;
2. alguem que encontra;
3. alguem que organiza sem virar mais uma pendencia;
4. alguem que conversa com inteligencia em cima do contexto vivo.

Portanto:

1. o runtime nao pode endurecer a UX;
2. a fluidez nao pode ser tratada como perfume opcional;
3. o host deve continuar sendo o lugar onde o Prumo “fala”;
4. a infraestrutura so vale se sustentar essa experiencia, nao se competir com ela.

## 6. Estrutura correta do sistema

### 6.1. Ha um Workspace, nao varios

O Prumo opera sobre uma pasta raiz unica.

Dentro dessa raiz, o usuario pode ter quantas subdivisoes fizerem sentido:

1. `Pessoal/`
2. `Trabalho/`
3. `Saude/`
4. `Familia/`
5. `Projetos/`
6. outras que a vida dele pedir

Mas a unidade canonica do sistema e uma so: o `Workspace` raiz do Prumo.

### 6.2. A topologia alvo do workspace

O runtime atual ainda cria um workspace flat de transicao. Isso resolve carpintaria, mas piora UX: a raiz fica com cara de bancada de oficina e o usuario nao sabe o que e interfone, o que e sala e o que e casa de maquinas.

A topologia alvo passa a ser esta:

1. **raiz minima** para wrappers de descoberta por host
2. **`Prumo/`** para memoria viva e arquivos autorais
3. **`/.prumo/`** para infraestrutura atualizavel do sistema

Em portugues simples:

1. a raiz vira campainha;
2. `Prumo/` vira a parte habitada;
3. `/.prumo/` vira a casa de maquinas.

O plano detalhado dessa transicao esta em [WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md).

### 6.3. O que fica na raiz

Na raiz devem ficar apenas os wrappers de descoberta:

1. `CLAUDE.md`
2. `AGENTS.md`
3. `AGENT.md`

Esses arquivos devem ser:

1. curtos
2. regeneraveis
3. apontadores para `/Prumo/AGENT.md`
4. claros sobre a porta curta de invocacao

Observacao importante:

`AGENT.md` continua sendo a direcao arquitetural desejada, mas nao deve bloquear a transicao se os hosts reais ainda estiverem consumindo melhor `CLAUDE.md` ou wrappers equivalentes. O ganho dessa camada de indirecao precisa ser provado em campo, nao presumido por elegancia.

### 6.4. Funcao de cada camada visivel

#### Raiz minima

Serve para:

1. descoberta por host
2. invocacao curta
3. orientacao inicial

Nao deve carregar memoria operacional, estado tecnico e scaffolding de sistema como se a raiz fosse deposito municipal.

#### `Prumo/`

E a area de memoria viva do usuario.

Aqui devem morar:

1. `AGENT.md` canonico do workspace
2. `PAUTA.md`
3. `INBOX.md`
4. `REGISTRO.md`
5. `IDEIAS.md`
6. `Agente/`
7. `Referencias/`
8. `Inbox4Mobile/`
9. `Custom/`

#### `/.prumo/`

E a area de sistema local.

Aqui devem morar:

1. `state/`
2. `cache/`
3. `logs/`
4. `manifests/`
5. `system/skills/`
6. `system/workflows/`
7. `system/scripts/`

### 6.5. Funcao de cada arquivo-raiz

#### `AGENT.md`

E o indice canonico desejado do sistema.

Deve:

1. declarar identidade do usuario;
2. declarar identidade do agente;
3. apontar a ordem de leitura;
4. apontar a topologia do workspace;
5. dizer o que e fonte de verdade e o que e wrapper;
6. orientar hosts a entrarem pelo lugar certo.

Mas esta camada deve ser introduzida com pragmatismo:

1. nao como dogma imediato;
2. nao ao custo de aumentar carregamento inutil de contexto;
3. nao sem validar consumo real por mais de um host.

#### `CLAUDE.md`

E um wrapper de compatibilidade para hosts do ecossistema Claude.

Nao e a fonte de verdade.

Deve:

1. apontar para `AGENT.md`;
2. carregar o contrato de invocacao do host;
3. evitar duplicacao de regra sistemica;
4. permanecer fino.

No curto prazo, `CLAUDE.md` pode continuar carregando mais responsabilidade pratica do que gostaríamos, desde que isso seja tratado como transicao e nao como novo canon.

#### `AGENTS.md`

E um wrapper de compatibilidade para ambientes que procuram esse arquivo por convencao.

Nao e a fonte de verdade.

Deve:

1. apontar para `AGENT.md`;
2. expor a mesma orientacao de entrada de forma adaptada;
3. servir hosts nao-Claude sem reinventar o Prumo.

#### `PAUTA.md`

E a frente viva do sistema.

Deve conter:

1. o que esta quente;
2. o que esta em andamento;
3. pendencias;
4. lembretes;
5. itens que exigem retorno;
6. limpeza assistida quando pertinente.

#### `INBOX.md`

E materia-prima ainda nao processada.

Nao deve virar deposito permanente.

#### `REGISTRO.md`

E a trilha historica operacional.

Serve para registrar:

1. decisoes;
2. fatos relevantes;
3. mudancas de contexto;
4. resolucoes;
5. o que foi feito e por que.

#### `Referencias/`

E o lugar de materiais de consulta, workflows e indices tematicos.

#### `_state/`

E o lugar do estado tecnico.

Nao e para virar gaveta de contexto semantico.

Importante:

1. neste documento, `_state/` significa **estado tecnico do Workspace do usuario**
2. artefatos internos de desenvolvimento, handover e revisoes cruzadas nao pertencem a esse territorio
3. a oficina do repo deve ser tratada como `.workbench/` (mesmo que o path fisico legado ainda nao tenha sido renomeado)

### 6.6. Area cinzenta: skills e workflows

Skills e workflows tem duas naturezas ao mesmo tempo:

1. parte deles e motor do sistema
2. parte deles pode virar personalizacao do usuario

O desenho correto nao e escolher um dos lados. E usar overlay.

Regra:

1. base do sistema em `/.prumo/system/`
2. overrides do usuario em `/Prumo/Custom/`
3. precedencia sempre `custom > system`
4. update nunca pisa em customizacao do usuario

Isso evita que cada update do produto vire reforma em apartamento alugado.

## 7. O que fica em cada camada

### 7.1. Fica no host

O host e a frente de experiencia.

Responsabilidades:

1. interpretar o pedido do usuario;
2. conversar com fluidez;
3. decidir quando chamar ou nao o runtime;
4. conectar assuntos;
5. sustentar a sensacao de operador inteligente;
6. decidir o que deve virar registro, pauta, contexto ou workflow;
7. compor a resposta final.

O host tambem precisa carregar:

1. persona do Prumo;
2. disciplina conversacional;
3. limites de prolixidade;
4. regras de tom;
5. restricoes de interacao como “uma pergunta por vez” quando isso fizer parte da experiencia desejada.

Essas coisas nao surgem magicamente de um LLM so porque a arquitetura ficou elegante.

Isso vale para:

1. plugin/skills do Claude;
2. plugin/skills do Codex;
3. adapter do Slack;
4. Antigravity ou host futuro equivalente.

### 7.2. Fica no runtime

O runtime e o backend de capacidades.

Responsabilidades:

1. OAuth e refresh de token;
2. integracoes com Google, Slack e afins;
3. snapshots;
4. automacoes;
5. cron e jobs;
6. repair do workspace;
7. geracao de previews;
8. sync de ativos do sistema;
9. indices tecnicos derivados;
10. validacoes estruturais;
11. operacoes deterministicas;
12. deteccao de drift, contradicao e crescimento ruim.

O runtime nao deve encapsular demais o que o host local ja faz bem.

Regra pratica:

1. integracoes externas e estado tecnico ficam no runtime;
2. operacao bruta e rapida sobre Markdown local nao deve ser obrigada a passar por wrappers pesados se o host tiver ferramentas nativas melhores.

Em portugues simples: Google fica no backend. `grep`, `regex` e edicao de arquivo local nao precisam virar procissao Python se isso piorar latencia e clareza.

### 7.3. Fica no Workspace

O Workspace e a memoria viva do usuario.

Ele guarda:

1. contexto estavel;
2. pendencias;
3. registros;
4. referencias;
5. workflows;
6. subdivisoes tematicas;
7. estado local relevante;
8. historico legivel sem depender do Prumo.

## 8. Persistencia de contexto como pilar do produto

Persistencia nao e acessorio. E motor.

Sem ela, o Prumo vira conversa esperta de curto prazo.

Com ela, o Prumo vira sistema de continuidade.

### 8.1. O que precisa ser persistido

1. identidade estavel do usuario;
2. fatos recorrentes;
3. dados de referencia;
4. pendencias vivas;
5. decisoes e desdobramentos;
6. materiais para consulta futura;
7. workflows repetiveis;
8. estado tecnico e de integracoes.

### 8.2. Como isso deve funcionar

O host decide semanticamente o que deve ser salvo.

O runtime pode:

1. validar jurisdicao do arquivo;
2. sugerir destino correto;
3. atualizar indices;
4. manter catalogos tecnicos;
5. detectar excesso ou drift;
6. propor limpeza.

Mas a inteligencia semantica do registro nao deve virar um subproduto burocratico do runtime.

Tambem nao deve virar improviso puro do host. Isso reforca a necessidade de orquestracao compartilhada.

## 9. Governanca documental

### 9.1. O problema

Arquivos locais so funcionam como memoria se houver:

1. nomes humanos;
2. jurisdicao clara;
3. catalogacao;
4. indices;
5. rotinas de limpeza;
6. politica de crescimento.

Sem isso, o sistema degrada em acumulacao.

### 9.2. Sistema formal de jurisdicao

Cada informacao precisa ter casa propria.

Exemplo:

1. pendencia viva em `PAUTA.md`
2. entrada bruta em `INBOX.md`
3. decisao em `REGISTRO.md`
4. referencia em `Referencias/`
5. informacao estavel do usuario em pasta tematica adequada
6. estado tecnico em `_state/`

### 9.3. Nomes de arquivos

Arquivos devem ser:

1. intuitivos para o usuario;
2. legiveis no Finder/Explorer;
3. pesquisaveis por texto;
4. estaveis para indexacao.

O modelo recomendado e hibrido:

1. nome humano primeiro;
2. metadado em frontmatter ou indice;
3. evitar codigos opacos como nome principal do arquivo.

### 9.4. Catalogacao e descoberta

O Prumo deve manter catalogos explicitos.

Idealmente em duas camadas:

1. indices humanos em Markdown
2. indices tecnicos derivados em `_state/`

Exemplos:

1. `Referencias/INDICE.md`
2. `Referencias/Artigos/INDICE.md`
3. `_state/catalog.json`
4. `_state/file-index.json`

O sistema nao deve depender so de:

1. busca textual cega;
2. embeddings opacos;
3. memoria improvisada do modelo.

Mas a primeira fase dessa camada deve ser proporcional ao estado real do produto.

No curto prazo, o minimo estrutural e:

1. jurisdicao clara;
2. nomes intuitivos;
3. indices humanos simples onde fizerem mais falta;
4. gatilhos de crescimento ruim;
5. limpeza segura;
6. backlog para catalogacao tecnica mais sofisticada depois.

### 9.5. Limpeza automatica vs assistida

Esta separacao e estrutural.

#### Automatizavel

Quando o risco semantico e baixo:

1. regenerar indices;
2. subcategorizar lista longa;
3. mover arquivo para pasta canonica;
4. compactar arquivos derivados;
5. arquivar snapshots tecnicos antigos;
6. deduplicar entradas identicas;
7. reconstruir catalogos.

#### Assistida

Quando ha risco editorial ou conceitual:

1. resumir `AGENT.md`;
2. reorganizar `PAUTA.md`;
3. resolver contradicoes;
4. fundir notas semanticamente proximas;
5. mudar taxonomia principal;
6. redistribuir contexto importante;
7. apagar ou arquivar informacao que possa mudar o comportamento do sistema.

Quando isso acontecer, o Prumo deve:

1. colocar o assunto na `PAUTA.md`;
2. explicar o motivo;
3. propor caminhos curtos;
4. fazer a limpeza em parceria com o usuario.

Essa regra precisa de um refinamento por host.

Em hosts locais e mais fortes, deve existir espaco para **delegacao otimista**:

1. limpar primeiro quando o risco semantico for baixo;
2. comunicar depois o que foi consolidado, movido ou reindexado;
3. evitar conversa tagarela para pedir permissao sobre cada espanador.

Tambem deve existir escalacao:

1. se a mesma higiene assistida for ignorada repetidamente;
2. o item sobe para quente na `PAUTA.md`;
3. o sistema para de ser educadamente repetitivo e passa a tratar o problema como risco de operacao.

## 9.6. Memoria do host vs memoria local do Prumo

Hosts podem ter memoria propria.

Isso cria risco de competicao entre:

1. memoria local do produto;
2. memoria nativa do host;
3. contexto carregado da sessao;
4. arquivos canonicamente lidos.

Esse conflito precisa ser tratado como risco arquitetural explicito.

O Prumo nao pode presumir que a memoria do host reforca a memoria local. Em alguns casos, ela pode distorcer, compactar ou concorrer com ela.

## 10. Instalacao e onboarding

### 10.1. Principio

Terminal pode continuar sendo o encanamento por um tempo.

O usuario nao pode sentir que esta conversando com o encanamento.

Mas onboarding nao deve entrar antes de as fundacoes criticas estarem firmes.

Mexer na porta cedo demais, enquanto:

1. o canon ainda esta solto;
2. a orquestracao ainda nao foi definida;
3. o destino do plugin ainda nao foi decidido;

e um jeito elegante de polir a recepcao enquanto a laje ainda range.

### 10.2. Requisitos de experiencia

1. instalacao com entrada simples;
2. linguagem amigavel desde a primeira linha;
3. pedir o nome do usuario como primeira pergunta;
4. tratar o usuario por esse nome desde entao;
5. progressive disclosure;
6. nada de despejar flags e subcomandos como vestibular.

### 10.3. Fluxo desejado

O fluxo ideal de primeira instalacao seria:

1. disparar um instalador simples;
2. perguntar “Como voce gostaria de ser chamado?”;
3. explicar em uma frase o que vai acontecer;
4. criar ou adotar a raiz do Workspace;
5. perguntar de forma amigavel quais hosts o usuario quer habilitar;
6. habilitar os adapters correspondentes;
7. oferecer integracoes depois, sem forcar tudo de uma vez.

### 10.4. O que a instalacao deve fazer

1. instalar a base tecnica do Prumo;
2. registrar o comando principal;
3. criar ou adotar a raiz do Workspace;
4. gerar os wrappers canonicamente;
5. gerar a estrutura documental minima;
6. habilitar os hosts escolhidos;
7. sincronizar ativos do sistema;
8. deixar claro o que e automatico e o que e autoral.

### 10.5. O que a instalacao nao deve fazer

1. despejar configuracoes demais na primeira passada;
2. sobrescrever arquivos autorais sem parceria;
3. obrigar usuario nao tecnico a decorar CLI;
4. confundir pasta de instalacao do sistema com a raiz do Workspace.

## 11. Atualizacao do core

### 11.1. O que pode atualizar sozinho

1. scripts do sistema;
2. adapters;
3. templates canonicamente controlados;
4. modulos de procedimento;
5. indices tecnicos derivados;
6. wrappers regeneraveis;
7. ativos internos de runtime.

### 11.2. O que nao pode ser sobrescrito silenciosamente

1. arquivos autorais do usuario;
2. contexto semantico;
3. decisoes registradas;
4. organizacao viva do Workspace;
5. taxonomias principais sem aprovacao.

### 11.3. Regra de ouro

Atualizacao automatica pode mexer na maquina.

Nao pode sair rearrumando a casa.

## 12. Multi-host sem esquizofrenia

### 12.1. O que deve ser comum

1. schemas;
2. modulos canonicos;
3. regras do sistema;
4. contratos de acao;
5. scripts deterministas;
6. runtime de capacidades;
7. estrutura do Workspace;
8. governanca documental.

Tambem deve ser comum:

9. contrato de orquestracao;
10. contrato de erro e fallback;
11. disciplina de persona portavel.

### 12.2. O que pode variar por host

1. tom da conversa;
2. affordances de interface;
3. slash commands;
4. superficie de invocacao;
5. formato da resposta;
6. grau de compactacao;
7. UX de cada ambiente.

Em alguns hosts, tambem pode variar:

8. o grau de delegacao otimista permitido;
9. quanto de ferramenta nativa local vale mais do que chamar wrapper.

### 12.3. O que nao pode acontecer

1. cada host inventar sua propria logica de sistema;
2. cada host reimplementar o motor;
3. plugin e runtime virarem duas inteligencias completas em competicao.

Tambem nao pode acontecer:

4. o runtime ser tao granular que obrigue o host a fazer micro-tool-chaining demais;
5. a persona do produto evaporar e ser substituida pela voz generica do fornecedor do modelo;
6. o fallback tecnico vazar para o usuario em linguagem de stack trace.

## 13. Slack

Slack deve ser tratado como:

1. canal exigido por contexto comercial;
2. adapter corporativo;
3. superficie funcional, nao referencial de UX.

Nao deve ser tratado como:

1. definicao do que o Prumo e;
2. host principal de experiencia;
3. parametro para endurecer o produto inteiro.

Em portugues simples: Slack pode ser uma porta. Nao deve virar o molde da casa.

## 14. Implicacoes praticas para o roadmap

### 14.1. O que deve ganhar protagonismo

1. plugins/skills como frente principal de experiencia;
2. adapters finos por host;
3. contrato de orquestracao compartilhada;
4. governanca documental proporcional ao estado atual;
5. portabilidade de persona e disciplina conversacional.

### 14.2. O que deve ser rebaixado

1. runtime como produto de UX;
2. runtime como narrador principal;
3. runtime como lugar onde “a alma do Prumo” mora.

### 14.3. O que deve continuar forte

1. runtime como infraestrutura;
2. runtime como backend de integracoes;
3. runtime como backend de memoria estrutural;
4. runtime como backend de automacoes e governanca.

E precisa continuar leve o bastante para nao virar atravessador desnecessario entre host forte e arquivo local simples.

## 15. Decisoes arquiteturais propostas

1. manter `Workspace` no singular como raiz unica do sistema;
2. manter `AGENT.md` como direcao canonica, mas sem transformá-lo em bloqueio prematuro;
3. manter `CLAUDE.md` e `AGENTS.md` como wrappers finos, aceitando transicao pragmatica;
4. recolocar plugins/skills no centro da experiencia;
5. redefinir o runtime como backend de capacidades;
6. formalizar um contrato de orquestracao compartilhada;
7. formalizar governanca documental como subsistema central, mas em escopo inicial proporcional;
8. separar limpeza automatica, assistida e delegacao otimista;
9. tornar a instalacao um onboarding amigavel, no momento certo da transicao;
10. manter atualizacao automatica restrita a ativos do sistema, nao a arquivos autorais;
11. sustentar multi-host com uma unica fonte de verdade;
12. tratar portabilidade de persona como ativo arquitetural do produto.

## 16. Pergunta-chave respondida

Sim, o desenho discutido e mais ou menos este:

1. o usuario instala a base do Prumo;
2. escolhe quais hosts quer habilitar;
3. cria ou adota a raiz unica do Workspace;
4. o sistema gera wrappers, estrutura e ativos minimos;
5. o runtime fica nos bastidores, oferecendo capacidades;
6. os hosts entregam a experiencia;
7. o core tecnico pode ser sincronizado;
8. a memoria viva do usuario continua local, legivel e governada.

Mas com uma ressalva fundamental:

o usuario nao deve sentir que “usa o runtime”.

Ele deve sentir que usa o Prumo no host que preferir, enquanto uma base instalada trabalha por baixo sem pedir medalha.

## 17. Conclusao

O melhor futuro do Prumo nao esta em escolher entre plugin e runtime como se um deles tivesse que matar o outro.

O futuro mais coerente e:

1. experiencia viva nos hosts bons;
2. operacao confiavel nos canais limitados;
3. runtime como motor;
4. Workspace local como memoria;
5. governanca documental como coluna estrutural;
6. uma so verdade sistemica.

Em frase curta:

o Prumo deve voltar a soar como um bom interlocutor e parar de pedir que a infraestrutura finja ser pessoa.
