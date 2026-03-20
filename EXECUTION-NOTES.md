# Execution Notes

Este arquivo guarda descobertas tecnicas que mudam a direcao do trabalho. Nao e diario de bordo. Nao e ata de condomínio. E o que nao pode morrer com a sessao.

## Regras

1. Registrar aqui apenas descobertas tecnicas que alterem arquitetura, estrategia de execucao ou criterio de debug.
2. Cada nota deve dizer o que foi observado, por que importa e qual decisao isso puxou.
3. Microtestes, comandos triviais e tentativas sem valor duravel nao entram.
4. Toda nota daqui deve ter espelho em issue relevante quando afetar roadmap ou execucao.

## 2026-03-20 — Tasks entrou no radar certo

### Descoberta

O item all-day ausente no Google Calendar tinha cheiro de `Tasks/Reminders`, não de bug de hora ou fuso.

### Por que importa

Deixar isso sem nome seria vender um briefing aparentemente completo com um buraco conhecido no chão. É o tipo de honestidade criativa que só funciona até o primeiro tornozelo quebrado.

### Decisao

1. incluir `https://www.googleapis.com/auth/tasks.readonly` nos escopos padrão do runtime;
2. coletar tarefas do dia via `Tasks API` quando o perfil já tiver o escopo;
3. quando não tiver, avisar no `snapshot-refresh` e no `briefing` que alguns lembretes do Google podem ficar de fora;
4. não deixar a falta desse escopo derrubar a integração inteira.

## 2026-03-19 — Runtime local antes do plugin

### Descoberta

A maior parte do atrito recente nao veio do produto Prumo em si, mas do acoplamento ao plugin do Claude/Cowork: marketplace congelado, botao de update morto, checkout local velho e versoes divergentes entre runtime, plugin e core do workspace.

### Por que importa

Esse ruido estava mascarando o estado real do produto e consumindo tempo de desenvolvimento em burocracia de host, nao em capacidade do Prumo.

### Decisao

Fase 1 passa a ser validada sem depender do plugin. O plugin vira adapter futuro, nao trilho obrigatorio de execucao.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — Browser auth direto entrou como fundacao da integracao Google

### Descoberta

Se a direcao arquitetural e Google API direta, fazia pouco sentido continuar sem uma porta de entrada oficial para consentimento do usuario. Estavamos com o canteiro de obra pronto e sem portao.

### Por que importa

Sem `auth` explicito, o runtime continuaria dependendo de atalhos e improvisos para qualquer integracao real com Calendar ou Gmail. Isso e arquitetura de palco: parece pronta de frente, mas atras so tem madeira e prego torto.

### Decisao

Entrou `prumo auth google`:

1. abre o navegador para OAuth direto com Google;
2. grava apenas estado/metadado em `_state/google-integration.json`;
3. envia token sensivel para o Keychain no macOS;
4. assume `pessoal` como perfil padrao nesta fase.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — Calendar e Gmail diretos entraram no `snapshot-refresh`

### Descoberta

Autenticar bem sem usar a conta para nada e' so um jeito sofisticado de pendurar cracha no vazio. A primeira entrega util tinha que ser o briefing trazendo agenda e email sem pedir favor ao Gemini.

### Por que importa

Foi aqui que a tese do runtime local saiu da fase "consigo conectar" e entrou na fase "consigo usar". Sem isso, a integracao Google continuaria sendo showroom.

### Decisao

1. `snapshot-refresh` passa a preferir Google APIs diretas quando houver conta conectada;
2. agenda vem da Calendar API;
3. email entra pela Gmail API com triagem conservadora;
4. fallback antigo via snapshot dual continua existindo para quando a fonte nova falhar.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — O briefing local funciona; o gargalo era a coleta dual

### Descoberta

No workspace laboratorio `aVida`, `migrate`, `context-dump` e `briefing` rodaram corretamente. O problema restante nao era o runtime nem o workspace, mas a coleta dual de agenda/email via Gemini.

### Por que importa

Sem essa separacao, qualquer falha externa parecia falha do briefing inteiro.

### Decisao

Criamos `prumo snapshot-refresh` e passamos a tratar agenda/email como cache local alimentado explicitamente, em vez de obrigar o briefing a carregar o mundo nas costas toda manhã.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — O auth check do Gemini era mais caro que o proprio refresh

### Descoberta

O script `prumo-google-dual-snapshot.sh` fazia um sanity check com `gemini -p "Diga apenas OK"` antes de consultar o MCP. Na pratica, esse check estava gastando tempo demais e virando parte relevante do timeout total. Em paralelo, `gemini mcp list` ja era suficiente para validar se o perfil estava vivo e se o MCP estava configurado.

### Por que importa

Estavamos pagando duas vezes pelo mesmo pedagio: primeiro para descobrir se o Gemini respirava, depois para fazer a consulta de verdade.

### Decisao

Remover o auth check textual, validar via `gemini mcp list`, executar os perfis em paralelo e aumentar moderadamente a janela do refresh explicito. O briefing continua preferindo cache; o refresh explicito ganha mais chance de sucesso sem transformar a manhã do usuário em fila de cartório.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — O gargalo remanescente e a consulta Gemini, nao mais o preflight

### Descoberta

Mesmo depois de remover o auth check redundante e adicionar resgate por perfil, o `snapshot-refresh` real no laboratorio `aVida` continuou expirando. Isso empurrou o tempo total para mais de um minuto sem produzir cache util.

### Por que importa

O problema deixou de ser custo administrativo antes da consulta. Agora o gargalo esta na propria consulta ao MCP via Gemini, provavelmente pela combinacao de ferramentas, perfis e prompt ainda pesado demais para esse caminho.

### Decisao

O proximo corte tecnico nao deve ser mais um aumento cego de timeout. Deve ser uma destas coisas:

1. reduzir o escopo da consulta e/ou separar agenda de email;
2. tornar o refresh orientado por perfil;
3. trocar a fonte dessa coleta por uma via local mais previsivel.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — Separar por escopo como fallback automatico so alongou o sofrimento

### Descoberta

Testar refresh conjunto, depois por perfil e depois por escopo pareceu inteligente no papel. Na pratica, isso esticou o tempo total sem entregar cache util no laboratorio `aVida`.

### Por que importa

Quando a estrategia de recuperacao piora a experiencia sem aumentar resultado, ela deixa de ser resiliencia e vira tortura educada.

### Decisao

Nao manter fallback automatico por escopo nesta fase. O proximo corte deve ser mais cirurgico: ou refresh explicitamente orientado por perfil, ou troca da fonte da coleta. Dividir tudo automaticamente so porque parece modular e' um bom jeito de esconder lentidao atras de arquitetura.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — Agenda sozinha e email sozinho tambem expiraram

### Descoberta

Mesmo restringindo o refresh ao perfil `pessoal` e depois testando `agenda` e `email` separadamente, o comando continuou estourando exatamente na mesma janela de timeout.

### Por que importa

Isso enfraquece a hipótese de que o problema era apenas volume da consulta combinada. O gargalo parece estar mais fundo no caminho Gemini+MCP usado para essa coleta.

### Decisao

Parar de apostar em cirurgias cosméticas no prompt como solução principal. O proximo corte deve questionar a fonte e o mecanismo de coleta, nao apenas a embalagem do pedido.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — Multi-conta sai do caminho da Fase 1

### Descoberta

Mesmo a conta `pessoal` isolada continua expirando no caminho atual. Manter multi-conta como requisito imediato so aumenta o atrito sem comprar capacidade nova.

### Por que importa

Escopo ruim e um jeito sofisticado de sabotar produto nascente.

### Decisao

Na Fase 1, o runtime assume um perfil Google principal (`pessoal`) por padrao. Multi-conta volta depois, quando o cano de uma conta so parar de vazar.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — A qualidade do runtime deixou de depender so de smoke

### Descoberta

Os smokes ja estavam pegando quebra grosseira, mas a base nova de Google API e fallback do briefing ainda ficava exposta a regressao silenciosa em funcao pequena: parser de email, merge de estado, cache do snapshot. Traduzindo: a cerca estava no terreno, nao nas janelas.

### Por que importa

Quando integracao externa e estado local se encontram, o produto costuma quebrar justamente no detalhe arrogante que "parecia obvio". Sem testes unitarios nos pontos certos, a gente so descobre isso depois que o usuario ja tomou na testa.

### Decisao

Entrou cobertura unitaria em `runtime/tests/` para quatro frentes:

1. parser e triagem de `google_api.py`;
2. serializacao/merge de `google_integration.py`;
3. fallback e cache de `commands/briefing.py`;
4. manutencao dos smokes como cerca de fluxo.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — O Google Console escondeu o JSON; o runtime parou de depender disso

### Descoberta

No fluxo real, o Google Auth Platform deixou o download do JSON menos acessivel e o client secret passou a aparecer como segredo gerado e mascarado. Isso transforma um onboarding simples numa gincana de UI.

### Por que importa

Se o produto depende de o usuario baixar um arquivo que o proprio console trata como reliquia, o problema deixa de ser "documentacao ruim" e vira acoplamento estupido a um fluxo externo caprichoso.

### Decisao

`prumo auth google` agora aceita dois caminhos:

1. `--client-secrets` com JSON;
2. `--client-id` + `--client-secret` diretamente.

Tambem blindamos o repo para `_secrets/`, `client_secret*.json` e `credentials*.json`, porque segredo versionado e so um vazamento que aprendeu Git.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — O Calendar API funcionou; a heuristica de proposta e que estava com faro torto

### Descoberta

No laboratorio `aVida`, a integracao direta finalmente trouxe agenda e email reais. O gargalo saiu da infraestrutura e mudou de andar: a `Proposta do dia` ainda conseguia puxar notificacao burocratica do Google Cloud como se fosse norte estrategico.

### Por que importa

Quando o produto escolhe um email banal como foco principal, ele nao parece cauteloso. Parece desorientado. E desorientacao com tom confiante e o jeito mais rapido de matar credibilidade.

### Decisao

1. billing/upgrade/ToS e parentes agora contam mais como ruido do que como estrela do palco;
2. itens `P1` e temas com cheiro real de acao ganham prioridade;
3. a proposta do dia passa a preferir pauta real antes de email `ver` que nao seja claramente acionavel.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — A UI do Google Calendar mostrou um item all-day que nao apareceu na Events API

### Descoberta

No laboratorio `aVida`, a integracao direta com Calendar API trouxe os eventos cronometrados corretos do dia, inclusive o jantar `Faísca c/ Flavio & Cris`. Mas a UI do Google Calendar tambem mostrava um item de dia inteiro ("Vai renovar a assinatura da Folha...") que nao apareceu no snapshot nem no briefing.

### Por que importa

Isso sugere um limite real do escopo atual: o briefing local pode estar lendo bem eventos de Calendar e ainda assim deixar passar itens exibidos na UI do Google Calendar que venham de outra fonte (por exemplo Tasks/Reminders ou calendario fora do recorte atual). Sem explicitar isso, o produto parece errado quando na verdade esta so olhando para uma fonte mais estreita.

### Decisao

Nao chamar isso de bug de formatacao. Tratar como gap de cobertura de fonte e deixar em backlog de integracoes:

1. validar se o item ausente vem de Google Tasks/Reminders;
2. decidir se Tasks entram como fonte formal do briefing em etapa futura;
3. enquanto isso, manter a comunicacao honesta: a Fase 1 cobre Calendar API e Gmail API, nao a cosmologia inteira da interface do Google.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-19 — Falha de token precisa parecer reauth, nao neblina

### Descoberta

Depois que a autenticacao direta finalmente funcionou, ficou obvio outro problema: quando o token morrer, o produto corre o risco de voltar a parecer "sem agenda" ou "sem email" sem dizer por que.

### Por que importa

Silencio operacional e so um bug que aprendeu etiqueta. Se o briefing nao disser quando a conexao esta viva, cansada ou morta, o usuario volta a discutir com sintoma.

### Decisao

1. o briefing passa a mostrar status explicito da integracao Google;
2. `invalid_grant` e equivalentes marcam o perfil como `needs_reauth`;
3. o briefing manda o usuario para `prumo auth google --workspace ...` quando necessario;
4. email vazio vira mensagem humana (`Nenhum email novo...`), nao silencio constrangedor.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)

## 2026-03-20 — Transparencia de estado sem virar debug de elevador

### Descoberta

Depois do bloco `Google` entrar no briefing, apareceram dois exageros opostos: ou o produto ficava mudo, ou falava como log técnico de porão. Faltava a faixa do meio.

### Por que importa

Produto que explica pouco vira adivinhação. Produto que explica demais vira painel de servidor. O briefing precisa ser painel de controle, não confessionário da API.

### Decisao

1. idade do refresh e do cache passa a ser mostrada em linguagem humana;
2. `email_display` e `email_note` se separam;
3. a heurística de `sinal fraco` deixa de ficar duplicada em dois arquivos.

Issue relacionada: [#41](https://github.com/tharso/prumo/issues/41)
