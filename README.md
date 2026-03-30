# Prumo

**Sistema de organização de vida pessoal com IA.**

Versão atual: **4.16.6**

Prumo não é mais só “o briefing esperto daquele plugin”. O produto agora está sendo empurrado para o lugar certo: um runtime local-first que funciona como organizador diário, facilitador de trabalho e base para workflows futuros.

Em português simples: briefing continua importante, mas não pode continuar sendo o apartamento inteiro. O valor do Prumo está em entender o estado do dia, propor a próxima jogada sensata, sustentar continuidade, atualizar documentação viva e deixar o trabalho menos pegajoso.

A decisao de MVP para Google agora e mais seca: os hosts usam seus conectores oficiais/MCP quando isso existir, e o Prumo consome esse material para briefing, acao e memoria local. A antiga trilha de Google APIs diretas no runtime ficou rebaixada para fallback/infra futura em [ADR-001-GOOGLE-INTEGRATION.md](/Users/tharsovieira/Documents/DailyLife/Prumo/ADR-001-GOOGLE-INTEGRATION.md).

O contrato de invocação do produto agora também está explícito em [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md). E a nova casa do canon compartilhado começou a sair do papel em [canon/](/Users/tharsovieira/Documents/DailyLife/Prumo/canon). Já era hora de parar de usar README como cartório improvisado.

O proximo corte do produto tambem ja ganhou planta propria em [WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md). Motivo simples: o `setup` atual ainda cria um workspace flat de transicao, com memoria viva e estado tecnico dividindo a mesma raiz como se isso fosse boa etiqueta.

Também ficou registrada, sem nostalgia boba e sem maquiagem de benchmark, a comparação entre o legado plugin-first e o runtime atual em [PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md](/Users/tharsovieira/Documents/DailyLife/Prumo/PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md). Esse documento existe para fixar o objetivo certo: recuperar a fluidez antiga sem recuperar o acoplamento antigo.

O próximo bloco operacional também já foi explicitado em [HOST-ADAPTER-IMPLEMENTATION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/HOST-ADAPTER-IMPLEMENTATION-PLAN.md). O ponto central ali é simples: mesma família de modelo não significa mesmo host. `Cowork` e `Claude Code` são adapters diferentes. `Gemini CLI` e `Antigravity` também.

O quadro de campo, hoje, está menos nebuloso e menos romântico:
`Antigravity` virou o trilho principal do primeiro piloto comercial, `Codex` é o host de referência técnica, `Claude Code` segue suportado no modo shell explícito, `Cowork` foi empurrado para backlog preparado e `Gemini CLI` saiu do foco ativo.

Esse plano agora também inclui um mapa de documentação oficial por host, porque desenhar adapter sem saber onde a documentação é sólida e onde ela é rala é um jeito elegante de construir ponte em neblina.

O runtime também passou a carregar, em `prumo start --format json`, metadados explícitos para adapter (`adapter_contract_version`, `workspace_resolution`, `adapter_hints`). Traduzindo: o host já não precisa bancar médium para descobrir qual porta usar.

E, agora, o `briefing` também fala JSON oficial quando o host precisar de estrutura em vez de prosa:

```bash
prumo briefing --workspace /caminho/do/workspace --refresh-snapshot --format json
```

O primeiro playbook host-específico também já existe: [CODEX-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CODEX-ADAPTER-PLAYBOOK.md). Não porque o Codex seja "mais importante", mas porque alguém precisa ser o primeiro trilho asfaltado.

O segundo playbook já deixa a taxonomia mais honesta: [CLAUDE-CODE-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CLAUDE-CODE-ADAPTER-PLAYBOOK.md). Ele existe justamente para impedir que `Claude Code` seja confundido com `Cowork` só porque ambos andam pela mesma família de modelos.

E o próximo corte já está preparado em [GEMINI-CLI-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/GEMINI-CLI-ADAPTER-PLAYBOOK.md). A lógica é simples: depois do `Codex` e do shell explícito no `Claude Code`, o próximo host limpo para validar campo é `Gemini CLI`, não o velho drama do `Cowork`.

Como o `Gemini CLI` resolveu improvisar runtime em vez de obedecer comando, o projeto já ganhou também [ANTIGRAVITY-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/ANTIGRAVITY-ADAPTER-PLAYBOOK.md). Nem todo primo do mesmo sobrenome merece herdar a culpa sem teste, mas também não merece cheque em branco.

O retrato de campo dos hosts, hoje, ficou assim:

1. `Antigravity` é o host principal do piloto e já respeita melhor o runtime do que a maior parte dos parentes.
2. `Codex` já passou como host de referência técnica.
3. `Claude Code` passou no shell explícito, mas ainda tropeça na invocação curta.
4. `Cowork` fica em backlog preparado. Em modo atual, ele mora numa sandbox/VM que não enxerga o runtime local do host. Insistir nisso agora seria hobby caro.
5. `Gemini CLI` foi reprovado como adapter porque tentou improvisar runtime e até mexeu em `_state/`.

Para o MVP, a aposta honesta é mais estreita: uma conta Google bem integrada via conector oficial do host já resolve muito do valor do produto sem transformar o Prumo em encanador de API alheia. O motor do Prumo também saiu do formato armário de acumulador: o core agora é índice + guardrails, com procedimento detalhado em módulos canônicos. E a sanitização deixou de ser só “compactar handover”: o sistema agora já consegue arquivar frio seguro com índice global, sem brincar de sumiço.

Seus dados ficam em arquivos Markdown no seu computador. Sem cloud, sem conta, sem lock-in.
E, a partir de agora, com um pouco mais de governo: o Prumo começou a explicitar o que pertence a `CLAUDE.md`, `PAUTA.md`, `REGISTRO.md` e histórico, em vez de fingir que tudo cabe no mesmo armário.

## O problema

Você tem 47 coisas na cabeça: o email que precisa responder, a reunião que precisa preparar, o exame que depende do pedido médico que você ainda não pediu. Aí você baixa um app de produtividade — e duas semanas depois ele virou mais uma pendência na lista de pendências.

Prumo funciona diferente: você despeja o caos, ele organiza. Sem dashboard pra manter, sem card pra arrastar, sem disciplina sobre-humana.

## Como funciona

1. **Captura** — Despeje tudo que está na sua cabeça. Texto, áudio, foto, email. Do computador ou do celular.
2. **Processamento** — Prumo separa, categoriza e extrai próximas ações. "Renovar passaporte, o Fulano manda o contrato amanhã e tive uma ideia de app" vira três itens em três contextos diferentes.
3. **Briefing diário** — Todo dia, Prumo traz o que importa: pendências, prazos, emails sem resposta, compromissos. Você só reage.
4. **Revisão semanal** — Varredura periódica pra nada cair do radar.

## Instalação

Prumo funciona com **Claude Desktop (Cowork)**, **Codex CLI** e **Gemini CLI**.

### Opção 1: Marketplace Git no Cowork (recomendada)

No Cowork, o caminho mais confiável hoje é adicionar o marketplace pelo repositório Git:

```text
https://github.com/tharso/prumo.git
```

Isso reduz o risco de catálogo congelado e evita boa parte da pantomima que a UI consegue encenar quando o checkout local envelhece parado.

### Opção 2: CLI canônico (backend do Claude)

Se você usa o backend do `claude` no terminal, este é o caminho canônico.
Para Cowork, ele ajuda, mas não substitui o store local do app quando a UI decide envelhecer sentada.

```bash
claude plugin marketplace add https://github.com/tharso/prumo.git
claude plugin install prumo@prumo-marketplace
```

Para atualizar depois:

```bash
claude plugin marketplace update prumo-marketplace
claude plugin update prumo@prumo-marketplace
```

Se quiser um instalador sóbrio, sem copiar comando em duas etapas:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_plugin_install.sh)
```

### Runtime local

É aqui que o produto realmente está sendo construído agora. O runtime já sustenta a porta curta (`prumo`), briefing estruturado, continuação de trabalho, documentação viva e estrutura pronta para workflows futuros.

No macOS ou Linux:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_runtime_install.sh)
```

Se você estiver mexendo no código do runtime e quiser instalação editável de verdade, clone o repo e rode o script local do checkout:

```bash
git clone https://github.com/tharso/prumo.git
cd prumo
bash scripts/prumo_runtime_install.sh
```

No Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_runtime_install.ps1 | iex
```

Depois:

```bash
prumo setup --workspace /caminho/do/workspace
cd /caminho/do/workspace
prumo start
prumo migrate --workspace /caminho/do/workspace
prumo snapshot-refresh --workspace /caminho/do/workspace
prumo snapshot-refresh --workspace /caminho/do/workspace --profile pessoal
prumo context-dump --workspace /caminho/do/workspace --format json
prumo inbox preview --workspace /caminho/do/workspace --format json
prumo briefing --workspace /caminho/do/workspace
prumo repair --workspace /caminho/do/workspace
```

Importante, para não vender andaime como se já fosse varanda:

1. `prumo ...` é a porta técnica do runtime hoje;
2. a UX final desejada do produto não é obrigar o usuário a decorar subcomandos;
3. o destino é o usuário abrir Cowork, Claude Code, Codex, Gemini CLI, Antigravity ou host equivalente e chamar o Prumo por uma porta curta (`/prumo`, `@Prumo`, `bom dia, Prumo` ou affordance parecida);
4. o host então deve encaminhar isso para o runtime local.
5. se o host consumir `prumo start --format json`, deve tratar `shell_command` e `host_prompt` como coisas diferentes. Máquina que tenta executar conversa vira liquidificador sem tampa.
6. se um comando falhar com erro explícito de uso, o host não deve repetir a mesma linha como se insistência fosse estratégia.
7. host bom também não sai rodando comando extra por tédio ou por confiança demais.
8. se quiser briefing estruturado, agora existe rota oficial. Inventar JSON na unha virou preguiça sem desculpa.

Em português simples: agora temos motor com porta de entrada decente e mais cara de produto diário. A ignição universal ainda depende dos hosts se comportarem como adultos.

O primeiro passo concreto nessa direção já existe:

```bash
cd /caminho/do/workspace
prumo
prumo start
```

`prumo` sem subcomando já cai em `start`. Não é a ignição universal final, mas pelo menos o binário deixou de responder com parser ferido quando o usuário só quer chamar o produto pelo nome. O comportamento continua o mesmo: tenta inferir o workspace pelo diretório atual (ou por um pai reconhecível), olha o estado do sistema e oferece briefing, retomada, repair ou auth/config sem pedir que o usuário adivinhe qual subcomando merece ser invocado naquela manhã.

Esse trilho cria:

1. `AGENT.md` como índice canônico do workspace;
2. `CLAUDE.md` e `AGENTS.md` como wrappers regeneráveis;
3. `Agente/` como diretório modular do contexto do usuário.

Importante, para nao vender a maquete como se ja fosse predio entregue:

1. o layout gerado hoje ainda e **flat e de transicao**;
2. a topologia alvo do produto passa a ser **raiz minima + `/Prumo/` + `/.prumo/`**;
3. o plano dessa migracao esta em [WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md);
4. o `setup` atual funciona, mas ainda nao oferece a experiencia final de adotar pasta existente, escolher modo de raiz e inaugurar a casa sem briefing de apartamento vazio.

Esses wrappers já não são só placa de "veja o balcão ao lado". Agora também carregam o contrato curto de invocação para hosts que leem arquivo antes de pensar:

1. se o usuário disser `Prumo`, o host deve rodar `prumo`;
2. se o pedido for briefing explícito, o host pode rodar `prumo briefing --workspace . --refresh-snapshot`;
3. se precisar de briefing estruturado, o host pode rodar `prumo briefing --workspace . --refresh-snapshot --format json`;
4. se souber renderizar ações, melhor ainda: `prumo start --format json`.

E agora também deixa uma fundação decente para integrações e plataforma:

1. `_state/google-integration.json` guarda estado e metadado da conexão;
2. token sensível fica fora do workspace;
3. no macOS, o runtime usa o Keychain;
4. fora do macOS, o runtime cai para storage local próprio do runtime, fora do workspace;
5. `context-dump` e `start --format json` agora expõem plataforma e capacidades de forma explícita.

E deixa uma coisa explícita, porque software adora esconder isso em rodapé: se você desinstalar o Prumo, seus arquivos continuam seus, legíveis e no mesmo lugar.

Se você já tem um workspace legado (com `CLAUDE.md` e `PRUMO-CORE.md` antigos), o caminho mais seguro agora é:

```bash
prumo migrate --workspace /caminho/do/workspace
```

Esse comando:

1. cria `AGENT.md` e o schema do workspace;
2. faz backup antes de sobrescrever wrappers e `PRUMO-CORE.md`;
3. preserva o `CLAUDE.md` legado em `Agente/LEGADO-CLAUDE.md`.

Se quiser abastecer agenda/email sem obrigar o briefing a esperar coleta ao vivo:

```bash
prumo snapshot-refresh --workspace /caminho/do/workspace
```

Esse comando tenta atualizar o cache local sem obrigar o briefing a ficar pendurado em coleta ao vivo. No MVP, a fonte preferencial de Google vem dos conectores oficiais do host. O runtime pode continuar existindo como trilha de fallback ou infra futura, mas deixou de ser a espinha dorsal dessa parte do produto.

Em português menos cerimonial:

1. host coleta Gmail, Calendar e Drive quando tiver conector oficial para isso;
2. Prumo consome o que vier dessa coleta;
3. briefing, triagem, continuidade e memória continuam sendo responsabilidade do Prumo;
4. integração Google dentro do runtime saiu do centro e foi para a reserva.

Descobertas tecnicas que mudam direcao agora ficam registradas em `EXECUTION-NOTES.md`. O objetivo e simples: nao repetir a mesma escavacao toda vez que um host resolver brincar de labirinto.

### Opção 3: Doctor e update do Cowork

Se o Cowork mostrar versão velha, deixar `Atualizar` morto ou jurar que está sincronizado enquanto lê jornal de ontem:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_cowork_doctor.sh)
```

Se o diagnóstico apontar checkout congelado do marketplace:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_cowork_update.sh)
```

Depois:
1. feche totalmente o Cowork;
2. abra o app de novo;
3. se ainda precisar, remova só o plugin `Prumo` e reinstale a partir do marketplace.

### Opção 4: Marketplace por URL raw na UI

Use a URL abaixo só como compatibilidade ou debug:

```text
https://raw.githubusercontent.com/tharso/prumo/main/marketplace.json
```

Observação importante:
o fluxo por `raw` pode parecer atualizado e continuar velho por baixo. Se o app disser "comando desconhecido", travar em versão antiga ou apagar o botão de update, trate isso como drift de catálogo. Não como azar metafísico.

### Opção 5: Upload local (.zip)

Baixe o repositório e instale manualmente como pacote local. Funciona, mas envelhece mal e cobra pedágio depois.

### Após instalar

1. Abra uma nova conversa na sua plataforma (Claude Desktop, Codex ou Gemini)
2. Selecione uma pasta no seu computador para o Prumo organizar seus arquivos
3. Digite `/setup`

O setup é um wizard conversacional — uma pergunta por vez, tudo reversível. Leva uns 15 minutos.

Se preferir ir direto ao ponto: `/start` — você despeja tudo que tem na cabeça e o sistema organiza na hora.

## Comandos

No Cowork, os slash commands do Prumo aparecem sem prefixo do plugin. Use `/setup`, `/briefing`, `/doctor`, `/handover`, `/sanitize`, `/higiene` e `/start`.

| Comando | O que faz |
|---------|-----------|
| `/setup` | Setup completo (wizard de 10 etapas) |
| `/start` | Onboarding rápido — despeje e o sistema organiza |
| `/briefing` | Briefing diário (pauta, inbox, calendário, emails) |
| `/doctor` | Diagnóstico do runtime do Prumo no Cowork (store, marketplace, drift de versão) |
| `/handover` | Handover entre agentes (abrir, responder, listar, fechar) |
| `/sanitize` | Sanitiza estado operacional e arquiva histórico frio com rastreabilidade |
| `/higiene` | Diagnostica e propõe limpeza assistida do `CLAUDE.md`, separando limpeza segura, confirmação factual, governança e avisando sobre core defasado |

## Princípios

- **Tudo local.** Arquivos Markdown em pastas do seu computador. Abra com qualquer editor.
- **Sem lock-in.** Deletou o plugin? Seus arquivos continuam lá — só que melhor organizados.
- **Uma entrada.** Sua vida não tem departamentos. Prumo também não.
- **Proativo.** Prumo não espera você checar. Traz o que importa na hora certa.

## Estrutura do repositório

```
├── plugin.json              # Manifest do plugin
├── marketplace.json         # Manifest do marketplace
├── runtime/                 # Runtime local-first do produto
├── commands/                # Slash commands (/setup, /briefing, etc.)
├── cowork-plugin/           # Pacote de runtime (skills, scripts, referências)
├── CHANGELOG.md             # Histórico de mudanças
└── VERSION                  # Versão atual
```

## Compatibilidade

- Claude Desktop (Cowork)
- Codex CLI
- Gemini CLI

## Diagnóstico rápido

Se aparecer "comando desconhecido" após instalar/atualizar, o suspeito principal é sessão velha, app sem restart, comando digitado com prefixo errado ou marketplace congelado num checkout velho.
Feche a conversa, abra uma nova, teste o autocomplete de `/setup`, `/briefing`, `/doctor`, `/handover`, `/sanitize`, `/higiene` e, se preciso, reinicie o Cowork antes de decretar bug no plugin.

Se o painel do app disser que atualizou, mas o plugin continuar em versão velha ou sumirem comandos novos, rode o `doctor` do Cowork. O painel às vezes sorri e não faz o serviço. Concierge de hotel ruim.

## Versão

Versão atual: `4.16.6`

## Licença

MIT

---

[prumo.me](https://prumo.me)
