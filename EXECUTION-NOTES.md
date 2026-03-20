# Execution Notes

Este arquivo guarda descobertas tecnicas que mudam a direcao do trabalho. Nao e diario de bordo. Nao e ata de condomínio. E o que nao pode morrer com a sessao.

## Regras

1. Registrar aqui apenas descobertas tecnicas que alterem arquitetura, estrategia de execucao ou criterio de debug.
2. Cada nota deve dizer o que foi observado, por que importa e qual decisao isso puxou.
3. Microtestes, comandos triviais e tentativas sem valor duravel nao entram.
4. Toda nota daqui deve ter espelho em issue relevante quando afetar roadmap ou execucao.

## 2026-03-20 — O runtime já existe; a invocação universal ainda não

### Descoberta

Depois que `prumo` virou comando real no sistema, ficou mais fácil separar duas coisas que estavam se misturando na conversa: ter um runtime local funcional e ter uma UX final decente de invocação dentro dos hosts. Hoje já dá para fazer teste sério pedindo ao host que execute `prumo ...`. Mas isso ainda não é a experiência-alvo.

### Por que importa

Sem registrar essa diferença, o time corre dois riscos igualmente irritantes:

1. achar que a UX já está resolvida só porque o CLI funciona;
2. ou achar que o runtime fracassou só porque a porta de entrada universal ainda não existe.

É a velha confusão entre motor e ignição.

### Decisao

1. documentar explicitamente que a estrela polar de UX é o usuário abrir o host e chamar o Prumo por uma porta curta (`/prumo`, `@Prumo`, `bom dia, Prumo` ou equivalente);
2. tratar `prumo ...` como contrato técnico canônico, não como experiência final canônica;
3. abrir a próxima frente de produto como `Invocation UX`, em vez de continuar mexendo só em encanamento e auth como se isso resolvesse entrada por osmose.

## 2026-03-20 — `prumo start` precisava parar de agir como formulário

### Descoberta

Depois da validação cruzada de `prumo start`, ficou claro que a porta de entrada ainda estava com vícios de CLI interna: exigia `--workspace` mesmo quando o usuário já estava parado dentro da pasta certa, sugeria auth Google com caminho-placeholder de laboratório e ainda cortava o menu antes de mostrar contexto em alguns estados.

### Por que importa

Uma porta de entrada que pede mais adivinhação do que orientação faz o produto parecer mais esperto no README do que no terminal. É o tipo de atrito pequeno que vai corroendo confiança sem fazer barulho.

### Decisao

1. fazer `prumo start` inferir o workspace pelo diretório atual ou por um pai reconhecível;
2. trocar a sugestão morta de auth Google por instrução executável ou ajuda real (`--help`) quando faltarem credenciais;
3. ampliar o menu para não esconder `context-dump` justamente quando ele pode evitar diagnóstico burro.

## 2026-03-20 — O runtime funcionava; o instalador é que ainda vivia em 2019

### Descoberta

O comando `prumo` ainda não existia como experiência real de usuário porque `scripts/prumo_runtime_install.sh` e `scripts/prumo_runtime_update.sh` usavam `python3 -m pip install --user -e ...` sem olhar para o ambiente. No macOS desta máquina, `python3` era o 3.9.6 do sistema, enquanto o projeto exige `>=3.11`. Resultado: o motor estava pronto, mas o usuário recebia um carrinho sem roda.

### Por que importa

Sem instalador confiável, todo teste “como usuário” virava teste de oficina com `PYTHONPATH=... python3 -m ...`. Isso serve para engenharia. Para produto, serve tanto quanto chave de fenda como maçaneta.

### Decisao

1. fazer `install` e `update` preferirem `uv tool install --editable --python 3.11`;
2. cair para `pip` só quando houver um Python 3.11+ de verdade;
3. alinhar `pyproject.toml` com a versão corrente do runtime;
4. validar o fluxo final com `which prumo`, `prumo --version` e comandos reais no workspace de laboratório.

## 2026-03-20 — O gargalo de Apple Reminders não era a lista; era o AppleScript lendo `due date`

### Descoberta

Mesmo limitando o escopo para uma lista só (`A vida...`), o fetch via AppleScript continuava empacando quando tentava ler `due date` item por item. Já o helper em Swift com `EventKit` devolveu o reminder de teste imediatamente e com a lista correta.

### Por que importa

Isso derruba uma premissa preguiçosa: não era “lista demais” nem “o briefing ainda está cru”. Era a tecnologia errada para o trecho mais sensível da coleta. Continuar insistindo em AppleScript ali seria como chamar alicate de relógio suíço.

### Decisao

1. usar `EventKit` como trilho principal de fetch para Apple Reminders;
2. deixar AppleScript como fallback e ponte, não como motor do dia a dia;
3. adicionar cache local e listas observadas para Apple Reminders, porque fetch vivo sem escopo claro é só um convite educado à lentidão.

## 2026-03-20 — Lista observada escondida em `auth` era UX de oficina, não de produto

### Descoberta

Depois de estabilizar Apple Reminders com `EventKit`, o próximo atrito não era mais técnico. Era ergonômico. Configurar `observed_lists` por `prumo auth apple-reminders --list ...` funciona, mas mistura pedir permissão com ajustar escopo.

### Por que importa

Quando configuração mora como efeito colateral de autenticação, o usuário não encontra onde mexer sem decorar sintaxe ou reler README como se fosse bula de antibiótico.

### Decisao

1. criar `prumo config apple-reminders`;
2. deixar esse comando mostrar estado atual, definir listas observadas ou voltar para “todas” com `--all`;
3. manter `auth apple-reminders --list ...` como atalho útil, não como único buraco da fechadura.

## 2026-03-20 — Tasks entrou no radar certo

## 2026-03-20 — O lembrete não era do Google; era da Apple usando o Calendário como vitrine

### Descoberta

O item “Vai renovar a assinatura da Folha...” e os novos lembretes criados pelo usuário não apareciam nem na `Calendar API` nem na `Tasks API`, mas a UI mostrava campos como `Lista`, `Etiquetas`, `Sinalizar`, `Prioridade`, `Localização` e `Ao Enviar Mensagem`. Isso é quase assinatura digital do app `Lembretes` da Apple.

### Por que importa

Sem essa distinção, qualquer tentativa de “resolver reminders” viraria escavação no cano errado. O Google não estava escondendo tudo; nós é que estávamos interrogando o suspeito errado.

### Decisao

1. tratar `Apple Reminders` como frente própria do runtime local;
2. considerar `Google Calendar + Gmail + Tasks` cobertura válida da Fase 1;
3. parar de chamar reminder da Apple de gap do Google só porque ele aparece na interface do Calendário.

## 2026-03-20 — EventKit puro em CLI bate no teto cedo; AppleScript autentica melhor, mas fetch ainda manca

### Descoberta

O helper em Swift com `EventKit` conseguiu provar viabilidade técnica, mas mostrou um limite estrutural para CLI: pedir permissão a `Reminders` sem bundle/Info.plist é um caminho meio torto. Ao trocar o auth para AppleScript (`osascript` falando com `Lembretes.app`), a permissão entrou e as listas ficaram visíveis. Já a coleta diária continuou instável em bases maiores: lenta demais em alguns testes e sensível a reminders com dados tortos em outros.

### Por que importa

Isso muda a abordagem. Não é mais “falta descobrir a API certa”. A API local já foi encontrada. O problema agora é qualidade operacional do trilho AppleScript para fetch recorrente.

### Decisao

1. manter `auth apple-reminders` como trilho experimental útil na Fase 1;
2. expor o estado Apple Reminders no `briefing` e no `context-dump`;
3. registrar explicitamente que o fetch diário ainda não está pronto para ser vendido como cobertura definitiva;
4. tratar a leitura de reminders Apple como frente separada de refinamento, não como bloqueio da integração Google.

### Descoberta

O item all-day ausente no Google Calendar tinha cheiro de `Tasks/Reminders`, não de bug de hora ou fuso.

### Por que importa

Deixar isso sem nome seria vender um briefing aparentemente completo com um buraco conhecido no chão. É o tipo de honestidade criativa que só funciona até o primeiro tornozelo quebrado.

### Decisao

1. incluir `https://www.googleapis.com/auth/tasks.readonly` nos escopos padrão do runtime;
2. coletar tarefas do dia via `Tasks API` quando o perfil já tiver o escopo;
3. quando não tiver, avisar no `snapshot-refresh` e no `briefing` que alguns lembretes do Google podem ficar de fora;
4. não deixar a falta desse escopo derrubar a integração inteira.

## 2026-03-20 — O Google não estava errado; a URL é que estava bêbada

### Descoberta

Depois da reauth com `tasks.readonly`, a `Tasks API` ainda falhava. O erro real mostrou `404` em uma rota montada como `/users/@me/lists/{id}/tasks`. Em bom português: o problema não era escopo, nem a API desligada. Era endpoint errado do nosso lado.

### Por que importa

Sem esse diagnóstico, o produto continuaria mandando o usuário reautenticar ou ativar API à toa. É o tipo de bug que não quebra tudo, só faz você perder tempo e confiança ao mesmo tempo.

### Decisao

1. corrigir a rota de tasks para `/tasks/v1/lists/{tasklist}/tasks`;
2. endurecer o teste unitário para validar a URL exata;
3. soltar isso como bugfix separado (`4.12.1`), em vez de fingir que o `4.12.0` já tinha nascido perfeito.

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
