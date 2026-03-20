# Fase 1: runtime local do Prumo

Status: plano de execucao consolidado

Relacionado:

1. [LOCAL-RUNTIME-TRANSITION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/LOCAL-RUNTIME-TRANSITION-PLAN.md)
2. Issue publica base: [#40](https://github.com/tharso/prumo/issues/40)
3. [ADR-001-GOOGLE-INTEGRATION.md](/Users/tharsovieira/Documents/DailyLife/Prumo/ADR-001-GOOGLE-INTEGRATION.md)
4. [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md)

## 1. Objetivo da Fase 1

Provar a tese do novo Prumo com o menor recorte que ainda sirva para gente nova e gente velha.

Essa prova precisa mostrar quatro coisas:

1. o runtime local consegue instalar/configurar o sistema no workspace do usuario;
2. o runtime local consegue executar o briefing via adapter fino;
3. o usuario continua dono absoluto dos arquivos dele;
4. o workspace continua legivel e util mesmo se o Prumo for desinstalado no dia seguinte.

Sem isso, a Fase 1 vira maquete de predio sem porta. Bonita para arquiteto. Irritante para morador.

Nota para ninguém se perder no caminho:

1. a Fase 1 está construindo e validando o runtime local;
2. ela ainda não entrega a UX final de invocação do produto dentro dos hosts;
3. a UX final desejada é o usuário abrir o host e chamar o Prumo por uma porta curta (`/prumo`, `@Prumo`, `bom dia, Prumo` ou equivalente), não por um subcomando cru.

## 2. Entregaveis da Fase 1

A Fase 1 inclui apenas:

1. `prumo setup`
2. `prumo start`
3. `prumo migrate`
4. `prumo snapshot-refresh`
5. `prumo auth google`
6. `prumo briefing`
7. `prumo context-dump`
8. `prumo repair`
9. adapter experimental do Cowork
10. fluxo de update do runtime local
11. trilha minima de migracao do workspace
12. trilha minima de documentacao de execucao
13. auth experimental de Apple Reminders no macOS, sem promessa ainda de cobertura total do briefing
14. configuracao CLI minima de listas observadas para Apple Reminders

Fora da Fase 1:

1. `handover` como comando do runtime
2. `higiene`
3. `sanitize` ou `faxina` como migracao completa de nomenclatura
4. `doctor` como comando nativo do runtime
5. conectores proprios
6. adapters para Codex, Gemini e IDEs
7. interface local de configuracao de email/calendario e outras fontes
8. multi-conta Google como comportamento padrao
9. cobertura definitiva de Apple Reminders no briefing diario
10. UX final de invocação dentro de cada host (`/prumo`, `@Prumo`, “bom dia, Prumo” ou equivalente)

## 3. Criterio de sucesso

Consideraremos a Fase 1 validada se um usuario novo conseguir:

1. instalar o runtime local sem precisar entender Python, virtualenv ou a fauna do terminal;
2. escolher um workspace com clareza sobre o que isso significa;
3. passar por um setup didatico e tranquilizador;
4. entender que desinstalar o Prumo nao apaga informacao nenhuma dele;
5. abrir o Cowork;
6. disparar `briefing`;
7. receber a resposta a partir do runtime local, nao de logica espalhada no plugin.

E se um usuario existente conseguir:

1. apontar o runtime para o workspace atual;
2. detectar drift de core/workspace;
3. regenerar wrappers ou arquivos recriaveis que sumiram;
4. receber briefing coerente sem regressao grosseira de contrato.
5. nao perder descobertas tecnicas que mudem direcao entre uma sessao e outra.

Isso valida a fundação. Não valida ainda a entrada final do produto.

## 3.1. O que ainda não está validado nesta fase

Ainda não consideraremos a Fase 1 falha só porque o usuário precise pedir ao host para executar `prumo ...`.

Esse atrito é real, mas pertence ao bloco seguinte:

1. `Invocation UX`
2. adapters finos que traduzam a invocação do host para `prumo start`
3. adapters finos por host para esconder o encanamento e expor uma porta humana

## 4. Decisoes tecnicas principais

### 4.1. Nucleo: biblioteca + CLI

O runtime nasce como:

1. biblioteca interna canonica;
2. CLI oficial por cima dela.

Motivo:

1. CLI resolve o uso humano e varios hosts simples;
2. biblioteca evita subprocesso burro para tudo;
3. adapters futuros podem chamar a biblioteca quando o host permitir.

Corolário importante:

1. o CLI é contrato técnico canônico;
2. ele não deve ser confundido com a experiência final canônica do usuário.

### 4.2. Principio de propriedade

Tudo que e do usuario continua no workspace do usuario.

Tudo que e engine continua fora do workspace.

Exemplo do que e do usuario:

1. `AGENT.md`
2. `CLAUDE.md`
3. `AGENTS.md`
4. `Agente/`
5. `PAUTA.md`
6. `INBOX.md`
7. `REGISTRO.md`
8. `_state/`

Exemplo do que e do runtime:

1. biblioteca
2. comandos
3. scripts internos
4. templates canonicos
5. adapters
6. manifests
7. cache tecnico do runtime

Esse principio e inegociavel. O Prumo nao pode virar corretor de imovel da vida alheia.

### 4.3. Estrutura de contexto do usuario

O workspace novo passa a ter uma porta de entrada canonica e um diretorio modular para contexto vivo.

Estrutura alvo:

```text
[Workspace]/
├── AGENT.md
├── CLAUDE.md
├── AGENTS.md
├── Agente/
│   ├── INDEX.md
│   ├── PESSOAS.md
│   ├── SAUDE.md
│   ├── ROTINA.md
│   ├── INFRA.md
│   ├── PROJETOS.md
│   └── RELACOES.md
├── PAUTA.md
├── INBOX.md
├── REGISTRO.md
└── _state/
```

Papeis:

1. `AGENT.md`: indice canonico e porta de entrada principal para qualquer host;
2. `CLAUDE.md`: wrapper regeneravel para Claude/Cowork;
3. `AGENTS.md`: wrapper regeneravel para ecossistemas que esperam esse nome;
4. `Agente/`: contexto modular do usuario, legivel e auditavel;
5. `_state/workspace-schema.json`: contrato tecnico da estrutura do workspace.

Objetivo:

1. aumentar chance de o host achar a informacao certa;
2. reduzir dependencia de um arquivo-monolito;
3. permitir reparo e regeneracao de wrappers sem amputar conteudo autoral.

## 5. Escopo tecnico detalhado

### 5.0. Porta de entrada final (destino, não entrega desta fase)

O comportamento-alvo do produto é:

1. o usuário chama o Prumo no host;
2. o runtime inspeciona o workspace;
3. a resposta inicial oferece uma destas trilhas:
   - briefing
   - continuar algo em andamento
   - setup
   - repair
   - auth/config quando faltar integração

Em outras palavras: o primeiro contato do usuário não deve ser um subcomando. Deve ser uma conversa com porta de entrada clara.

O que a Fase 1 faz é deixar o runtime pronto para que essa porta exista no bloco seguinte.

O primeiro slice disso já entrou: `prumo start` como porta de entrada do runtime. Ele já tenta inferir o workspace pelo diretório atual antes de exigir `--workspace` como senha de repartição. O que ainda falta é o host bater nessa porta por conta própria.

### 5.1. `prumo setup`

Responsabilidade:

1. perguntar como o usuario prefere ser chamado;
2. explicar em linguagem humana o que e um workspace;
3. explicar o que o Prumo vai criar e o que nao vai tocar;
4. deixar explicito que desinstalar o Prumo nao faz o usuario perder informacao nenhuma;
5. criar ou preparar o workspace;
6. validar estrutura minima;
7. materializar arquivos canonicos faltantes;
8. registrar versao do runtime e do setup aplicado;
9. nunca atropelar personalizacao sem backup.

Saida esperada:

1. usuario passa a ser tratado pelo nome escolhido;
2. workspace pronto para briefing;
3. `AGENT.md` presente como indice canonico;
4. wrappers `CLAUDE.md` e `AGENTS.md` presentes e regeneraveis;
5. registro claro do que foi criado, preservado, migrado ou deixado intacto;
6. mensagem explicita de seguranca sobre reversibilidade e ausencia de lock-in.

### 5.2. `prumo migrate`

Responsabilidade:

1. adotar um workspace legado no trilho novo;
2. criar `AGENT.md` e schema tecnico;
3. sobrescrever wrappers e `PRUMO-CORE.md` com backup antes;
4. preservar contexto legado em arquivo acessivel;
5. evitar que a migracao dependa de telepatia do usuario ou coragem cega.

Saida esperada:

1. workspace antigo vira workspace adotado;
2. backup claro e local do que foi substituido;
3. `Agente/LEGADO-CLAUDE.md` quando houver contexto legado importado;
4. trilho novo operacional sem apagar a autobiografia do usuario no processo.

### 5.3. `prumo briefing`

Responsabilidade:

1. ler contexto do workspace;
2. aplicar modulos canonicos;
3. detectar drift de versao/core;
4. executar briefing progressivo;
5. devolver resposta estruturada ao adapter.

Importante:

1. o contrato de interface atual deve ser preservado;
2. preflight de versao continua obrigatorio;
3. snapshots e integracoes pragmaticas continuam validos;
4. o briefing nao deve depender do wrapper `CLAUDE.md` para achar o contexto se o `AGENT.md` estiver presente.

### 5.4. `prumo snapshot-refresh`

Responsabilidade:

1. atualizar explicitamente o cache local de agenda/email;
2. desacoplar coleta externa da resposta do briefing;
3. permitir automação futura sem obrigar o usuário a esperar integração ao vivo toda manhã;
4. registrar com honestidade quando a fonte viva falhar e quando o runtime estiver só reaproveitando memória local.

### 5.5. `prumo auth google`

Responsabilidade:

1. abrir autenticacao Google no navegador;
2. conectar a conta principal do workspace sem depender de host externo;
3. guardar metadado de integracao no workspace;
4. guardar token sensivel fora do workspace, em storage seguro local;
5. deixar explicito qual conta e quais escopos foram conectados.

Diretriz:

1. na Fase 1, a conta principal padrao continua sendo `pessoal`;
2. o workspace guarda estado e metadado, nao credencial em texto puro;
3. no macOS, o storage sensivel vai para o Keychain;
4. multi-conta continua backlog, nao pretexto para atrasar o primeiro cano que precisa funcionar.
5. o onboarding nao pode depender exclusivamente de download de JSON pelo Google Cloud; `client_id` + `client_secret` diretos tambem sao trilho aceitavel quando a UI resolver brincar de esconde-esconde.

### 5.6. Coleta Google direta na Fase 1

Responsabilidade:

1. usar Calendar API direta como fonte primaria de agenda quando houver conta conectada;
2. usar Gmail API direta como fonte primaria de email quando houver conta conectada;
3. manter o cache local como trilho normal do briefing;
4. deixar o fallback anterior vivo enquanto a fonte nova ainda esta ganhando musculo;
5. expor no briefing o estado da integracao Google e o caminho de reauth quando o token cansar.

Guardrails:

1. triagem de email nesta fase pode ser conservadora; melhor isso do que banca de adivinhacao;
2. o briefing deve dizer de onde vieram agenda e email;
3. se a fonte direta falhar, o runtime cai para cache ou snapshot dual em vez de fingir onisciencia.
4. o briefing deve mostrar estado Google e idade do refresh sem obrigar o usuário a fazer conta de cabeça;
5. notas internas de integração não devem vazar para a superfície do produto como se fossem texto final.

### 5.6.1. Apple Reminders experimental no macOS

Responsabilidade:

1. reconhecer quando os “lembretes” do usuário são Apple, não Google;
2. autenticar acesso local ao app `Lembretes`;
3. expor estado e listas visíveis no workspace;
4. não fingir que a coleta diária já está pronta quando ela ainda está temperamental.

Guardrails:

1. auth local no macOS pode entrar antes da coleta completa;
2. se o fetch diário falhar ou ficar lento, isso vira estado explícito no briefing, não sumiço silencioso;
3. Apple Reminders nesta fase é trilho experimental, não cobertura prometida como se já estivesse estável.
4. listas observadas configuráveis entram antes de qualquer ambição multi-lista “mágica”;
5. cache local de Apple Reminders deixa de ser luxo e passa a ser requisito mínimo de sanidade operacional.

### 5.7. `prumo context-dump`

Responsabilidade:

1. expor um resumo objetivo do workspace para hosts/LLMs;
2. reduzir necessidade de cada adapter reinventar leitura inicial;
3. servir de alimentacao leve para conversa e comando.

Formato desejado:

1. JSON estruturado
2. opcao Markdown resumida

Conteudo minimo:

1. `workspace_path`
2. versao do runtime
3. versao do schema do workspace
4. versao do core/workspace
5. caminhos canonicos (`AGENT.md`, `Agente/`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`)
6. sinais de drift
7. capacidades disponiveis

### 5.6. `prumo repair`

Responsabilidade:

1. validar a estrutura esperada do workspace;
2. detectar arquivos obrigatorios ausentes;
3. recriar wrappers e arquivos gerados/recriaveis;
4. acusar com clareza a ausencia de arquivos autorais;
5. oferecer restauracao de backup quando houver;
6. nunca inventar conteudo autoral sem explicitar isso.

Principio:

1. o Prumo nao impede o usuario de apagar os arquivos dele;
2. o Prumo detecta cedo, repara o que for recriavel e fala a verdade sobre o resto.

### 5.7. Adapter experimental do Cowork

Responsabilidade:

1. receber o comando no Cowork;
2. passar `workspace_path`, comando e input para o runtime;
3. renderizar a resposta;
4. evitar pos-processamento complexo.

Pergunta que o spike precisa responder:

1. o Cowork consegue chamar o runtime local via shell com previsibilidade suficiente?

Se sim, otimo.
Se nao, o adapter fino precisara engordar um pouco. Melhor descobrir isso agora do que fingir que o shell vai se comportar como mordomo ingles.

## 6. Contratos que precisam existir

### 6.1. Contrato do CLI

Exemplo:

```bash
prumo setup --workspace /caminho
prumo migrate --workspace /caminho
prumo snapshot-refresh --workspace /caminho
prumo briefing --workspace /caminho
prumo context-dump --workspace /caminho --format json
prumo repair --workspace /caminho
```

### 6.2. Contrato do adapter

Entrada minima:

1. `workspace_path`
2. `command`
3. `raw_user_input`
4. `host_name`
5. metadados opcionais de sessao

### 6.3. Contrato de saida

O runtime deve devolver estrutura que permita:

1. renderizacao limpa no Cowork;
2. resposta textual consistente;
3. futura reutilizacao em outros adapters.

### 6.4. Contrato de documentacao local

O runtime deve registrar localmente o que nao pode morrer com a sessao.

Inclui, no minimo:

1. decisoes tomadas;
2. mudancas de estado relevantes;
3. tarefas criadas, alteradas ou concluidas;
4. reflexoes com valor futuro claro;
5. setup, migracoes e reparos estruturais.

Nao inclui, por obrigacao:

1. toda conversa exploratoria;
2. brainstorm sem consequencia;
3. cada suspiro dramatico do host.

### 6.5. Contrato de documentacao de execucao

O projeto tambem precisa registrar descobertas tecnicas que mudem direcao, sem virar prontuario infinito de shell.

Artefatos:

1. `EXECUTION-NOTES.md` no repo para descobertas com valor duravel;
2. comentario na issue de execucao correspondente quando a descoberta afetar roadmap, escopo ou estrategia.

Regra:

1. registrar apenas o que muda arquitetura, criterio de debug ou plano;
2. nao registrar microteste sem valor futuro;
3. preferir nota curta e util a ata de condomínio.

## 7. Estrategia de distribuicao da Fase 1

Nao vamos inventar foguete para ir a padaria.

Distribuicao inicial recomendada:

1. bootstrap previsivel;
2. runtime em Python;
3. instalacao guiada por script;
4. uso opcional de `uv` ou caminho semelhante para reduzir friccao;
5. experiencia que nao exige do usuario entender ambiente Python.

Objetivo:

1. ser simples para desenvolver;
2. simples para testar;
3. simples para migrar depois;
4. amigavel para usuario leigo.

Nao objetivo:

1. resolver cross-platform definitivo ja na primeira mordida.

## 8. Estrategia de coexistencia

Durante a Fase 1:

1. o plugin atual continua existindo;
2. o fluxo atual continua operacional;
3. o runtime novo vive em trilho paralelo;
4. o adapter experimental do Cowork aponta para o runtime novo so quando explicitamente habilitado.

Isso pode ser feito com:

1. branch propria;
2. worktree separado;
3. flags de execucao;
4. docs explicitas de modo experimental.

## 9. Riscos especificos da Fase 1

1. `setup` ficar ambicioso demais e virar reescrita do produto inteiro;
2. adapter do Cowork depender de shell de forma fragil;
3. `context-dump` virar dump gigante e inutil;
4. modularizar contexto do usuario sem dar navegacao canonica decente;
5. o usuario apagar wrappers ou arquivos importantes e ficar sem trilha de reparo;
6. duplicar logica entre runtime novo e plugin atual por tempo demais;
7. a experiencia parecer dois produtos sem parentesco.

## 10. Mitigacoes

1. manter Fase 1 presa a `setup`, `briefing`, `context-dump` e `repair`;
2. fazer spike do Cowork cedo;
3. definir saida estruturada minima antes de codar adapter;
4. registrar explicitamente o que continua no fluxo legado;
5. usar `AGENT.md` como indice canonico brutalmente claro;
6. tratar `CLAUDE.md` e `AGENTS.md` como wrappers regeneraveis;
7. introduzir `_state/workspace-schema.json` cedo;
8. comparecer com `repair` antes de prometer robustez.

## 11. Ordem recomendada de execucao

1. definir `workspace-schema` e a estrutura `AGENT.md` + `Agente/`;
2. definir templates canonicos do workspace;
3. extrair biblioteca minima;
4. expor CLI minima;
5. implementar `context-dump`;
6. implementar `setup`;
7. implementar `repair`;
8. implementar `briefing`;
9. fazer spike do Cowork chamando o runtime;
10. ajustar adapter experimental;
11. validar com workspace novo e workspace real.

## 12. Criterios de aceite da Fase 1

1. `setup` prepara workspace novo sem mutilar o usuario;
2. `setup` pergunta como o usuario quer ser chamado;
3. `setup` deixa explicito que tudo e do usuario e nada depende do Prumo para continuar existindo;
4. `AGENT.md` vira a porta de entrada canonica do contexto;
5. `CLAUDE.md` e `AGENTS.md` podem ser regenerados sem drama;
6. `repair` recompõe o que for recriavel e acusa o resto com clareza;
7. `briefing` roda pelo runtime local;
8. `context-dump` serve ao adapter sem virar despejo de contexto;
9. Cowork consegue chamar o runtime local com estabilidade razoavel;
10. drift entre workspace e runtime e detectado explicitamente;
11. fluxo legado continua disponivel enquanto o novo ainda e experimental.

## 13. Perguntas que ainda ficam em aberto

1. nome final do diretorio modular (`Agente/` ou variante melhor);
2. forma inicial de bootstrap (`uv`, script puro, outra);
3. formato final de saida do `context-dump`;
4. modo de habilitacao do adapter experimental no Cowork;
5. quando `faxina` vira nome de produto e `sanitize` fica so como nome tecnico;
6. onde exatamente termina Fase 1 e comeca Fase 2 sem truque retorico.

## 14. Backlog ja assumido para a fase seguinte

Quando a Fase 1 deixar de tossir, a proxima camada de produto deve incluir uma interface local de configuracao de fontes.

Para evitar teatro cedo demais, a Fase 1 assume um perfil Google principal (`pessoal`) por padrao. Multi-conta volta quando uma conta so parar de sangrar.

Escopo minimo desejado:

1. cadastrar contas e fontes de email;
2. cadastrar calendarios e definir quais entram no briefing;
3. mostrar claramente quais fontes estao ativas por workspace;
4. testar conexao, credenciais e freshness de snapshot;
5. explicitar fallback e prioridade de fontes sem exigir fe do usuario;
6. manter tudo local, auditavel e desinstalavel sem levar embora dado do usuario.
7. incluir Google Tasks API como proxima fonte formal para cobrir itens all-day que a `events.list` nao enxerga;
8. tratar Reminders como fora de escopo ate aparecer uma rota menos pantanosa.
9. tornar reauth de escopo novo (`tasks.readonly` e afins) explicito o bastante para o usuario nao precisar virar detetive do que sumiu no briefing.

Nao objetivo:

1. enterrar isso em arquivo obscuro e chamar de UX;
2. depender de plugin ou marketplace para o usuario entender qual conta o Prumo esta lendo.
