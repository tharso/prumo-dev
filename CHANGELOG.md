# Changelog

Este arquivo registra mudanças públicas do produto Prumo.

O formato segue, de forma pragmática, a ideia de Keep a Changelog e versionamento semântico.

## [4.15.4] - 2026-03-21

### Changed
- `prumo start --format json` agora expõe `adapter_contract_version`, `workspace_resolution` e `adapter_hints`, para o adapter parar de jogar tarô em cima do runtime.
- Os wrappers gerados do workspace (`AGENT.md`, `CLAUDE.md`, `AGENTS.md`) agora dizem explicitamente que host bom lê esses metadados antes de inventar moda.

### Docs
- O contrato de invocação e o plano de adapters foram alinhados a esse JSON mais explícito, porque chamar isso de "detalhe de implementação" seria um ótimo jeito de quebrar cinco hosts ao mesmo tempo.

## [4.15.3] - 2026-03-20

### Changed
- `prumo start --format json` agora separa ação de shell e continuação conversacional com `kind`, `shell_command` e `host_prompt`, em vez de jogar tudo em `command` e esperar que o host seja vidente.
- O contrato de invocação passou a dizer isso com todas as letras, para Codex, Cowork, Gemini e companhia pararem de tratar prosa como terminal.

### Docs
- Novo [HOST-ADAPTER-IMPLEMENTATION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/HOST-ADAPTER-IMPLEMENTATION-PLAN.md) explicitando a próxima trilha: adapters por host, com taxonomia clara de que mesma família de modelo não significa mesmo adapter (`Cowork != Claude Code`, `Gemini CLI != Antigravity`).
- O plano de adapters agora inclui uma matriz de documentação oficial por host, distinguindo onde o terreno é sólido (`Codex`, `Claude Code`, `Gemini CLI`) e onde a execução ainda depende mais de teste de campo (`Cowork`, `Antigravity`).

## [4.15.2] - 2026-03-20

### Added
- `AGENTS.md` e `CLAUDE.md` gerados pelo runtime agora carregam instruções curtas de invocação (`Prumo` -> `prumo`, briefing explícito -> `prumo briefing --workspace . --refresh-snapshot`), em vez de só mandar o host "ler o outro arquivo" e rezar.
- Nova suíte `runtime/tests/test_templates.py` cercando esse contrato nos wrappers.

### Changed
- O template canônico `agents-md-template.md` parou de tratar adapter para Codex e afins como compatibilidade muda. Agora ele assume, em texto claro, que host bom bate em `prumo` e deixa o runtime dirigir.

## [4.15.1] - 2026-03-20

### Changed
- `prumo` sem subcomando agora cai em `start`, em vez de responder com erro de parser como se o usuário tivesse digitado o nome do produto de forma ofensiva.

### Fixed
- O smoke principal do runtime deixou de validar só `start` explícito e passou a cercar também a rota curta (`prumo` puro), que é justamente a que interessa para host e para gente normal.

## [4.14.1] - 2026-03-20

### Added
- Novo [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md) registrando sem ambiguidade qual é a porta técnica atual (`prumo start`) e qual é a UX final desejada por host (`/prumo`, `@Prumo`, `bom dia, Prumo` ou equivalente).
- O bridge experimental do Cowork agora entende `start`, o que finalmente permite tratar invocação curta como adapter de verdade e não só como briefing com fantasia.

### Changed
- `prumo start` agora aceita override do caminho de client secrets via `PRUMO_GOOGLE_CLIENT_SECRETS`, em vez de depender só do caminho default de laboratório.
- A descoberta automática de workspace por CWD ganhou limite de profundidade. Subir até `/` toda vez não era pecado mortal, mas também não era exatamente sinal de juízo.
- O `SKILL.md` de briefing e o módulo `cowork-runtime-bridge.md` passaram a dizer explicitamente que a porta curta do host deve bater em `start`, não pular direto para briefing por reflexo condicionado.

### Fixed
- O bridge do Cowork deixou de bloquear `start` em workspace legado. Seria uma façanha bem idiota impedir justamente o comando que sabe mandar migrar.

## [4.15.0] - 2026-03-20

### Changed
- `prumo start` agora tenta inferir o workspace pelo diretório atual ou por um pai reconhecível antes de pedir `--workspace` como se o usuário estivesse solicitando visto.
- O menu de ações do `start` ganhou mais espaço e deixou de esconder `context-dump` quando o estado fica mais carregado.
- A sugestão de auth Google deixou de apontar para `/caminho/do/client_secret.json` como se placeholder fosse plano de produto. Se houver credencial padrão ou variáveis de ambiente, ele usa isso; se não houver, aponta para `--help` sem cinismo.

### Fixed
- Workspaces canônicos com `CLAUDE.md` e `PRUMO-CORE.md` presentes deixaram de correr risco de serem tratados como “legado” só porque ainda carregam wrappers.

## [4.14.0] - 2026-03-20

### Added
- Novo comando `prumo start` como porta de entrada canônica do runtime. Ele olha o estado do workspace e oferece o próximo caminho sensato, em vez de obrigar o usuário a adivinhar se hoje a palavra mágica é `briefing`, `repair` ou `auth`.
- Nova suíte `runtime/tests/test_start.py`, cobrindo workspace ausente, workspace legado, workspace saudável e saída JSON das ações sugeridas.

### Changed
- A documentação agora separa melhor duas coisas que estavam se agarrando pela gola: o contrato técnico (`prumo ...`) e a UX final desejada do produto (`/prumo`, `@Prumo`, `bom dia, Prumo` ou equivalente no host).
- `local_runtime_phase1_smoke.sh` passou a validar também a porta de entrada `start`, porque feature sem cerca de teste vira folclore rápido.

### Fixed
- O instalador e o updater do runtime deixaram de confiar cegamente no Python 3.9 do macOS e passaram a preferir `uv` com Python 3.11. O produto finalmente consegue ser testado como usuário, não só como mecânico.

## [4.13.2] - 2026-03-20

### Added
- Novo comando `prumo config apple-reminders` para mostrar, afunilar ou limpar listas observadas sem obrigar o usuário a usar o comando de auth como chave inglesa.

### Changed
- A configuração de `observed_lists` deixou de morar só em `prumo auth apple-reminders --list ...`. Agora ela tem endereço próprio no CLI, o que é bem melhor do que tratar configuração como efeito colateral.

## [4.13.1] - 2026-03-20

### Added
- Apple Reminders agora guarda cache local em `_state/apple-reminders-snapshot.json`, porque rodar a mesma consulta lenta a cada briefing seria uma forma criativa de chamar desperdício de “tempo real”.
- `prumo auth apple-reminders` passou a aceitar `--list` repetido para limitar as listas observadas. Vasculhar 21 listas para achar um lembrete doméstico era método, não inteligência.

### Changed
- O fetch de Apple Reminders passou a preferir `EventKit` via helper Swift e deixou AppleScript como fallback. O motor saiu da Kombi e entrou no carro.
- O `briefing` agora reaproveita cache de Apple Reminders e diz explicitamente quando está observando listas específicas.
- O `context-dump` expõe as listas observadas de Apple Reminders, porque “todas” e “uma só” são estados diferentes, por mais que a UI preguiçosa finja o contrário.

### Fixed
- `briefing --refresh-snapshot` voltou a propagar o refresh para a trilha Apple em todos os caminhos, em vez de esquecer esse detalhe justamente onde a água passava.
- O fetch diário de Apple Reminders deixou de empacar no `due date` do AppleScript quando havia uma lista observada clara. O problema não era a vida do usuário; era a ferramenta errada para a parte sensível.

## [4.13.0] - 2026-03-20

### Added
- Novo comando `prumo auth apple-reminders` para autenticar o runtime local no app `Lembretes` do macOS. O Prumo parou de olhar para lembrete da Apple e chamar isso de mistério do Google.
- Novo estado derivado `_state/apple-reminders-integration.json`, com status, listas visíveis e último refresh da integração Apple Reminders.
- O `briefing` e o `context-dump` agora expõem o estado de Apple Reminders separadamente do Google, porque misturar os dois só produz diagnóstico com cheiro de porão úmido.
- Nova suíte unitária `runtime/tests/test_apple_reminders.py` cobrindo estado local e resolução do helper.

### Changed
- O runtime passou a identificar explicitamente que reminders vistos no Apple Calendar podem vir do ecossistema Apple, não do Google. Parece detalhe de taxonomia até você perceber que estava abrindo a porta do apartamento errado.
- A integração Apple Reminders usa AppleScript como trilho principal de auth/local access no macOS CLI, porque o caminho EventKit puro sem bundle/Info.plist mostrou joelho mole para pedir permissão.

### Known limitations
- A autenticação Apple Reminders funciona, mas a coleta diária ainda está experimental: em bases maiores, o AppleScript do `Lembretes` pode ficar lento ou tropeçar em itens tortos. Em bom português: já temos a chave, ainda não temos a fechadura com bom amortecedor.

### Fixed
- A chamada da `Tasks API` estava usando a rota errada (`/users/@me/lists/{id}/tasks`) e recebia `404` com a convicção de quem acha que está certo. Agora usa a rota correta (`/lists/{id}/tasks`) e parou de culpar o Google por um tropeço nosso.
- O teste unitário de `fetch_tasks_today()` ficou mais rígido e agora acusa URL torta em vez de deixar bug passar de fininho com crachá de sucesso.

## [4.12.0] - 2026-03-20

### Added
- O runtime passou a incluir `Google Tasks API` no pacote de escopos padrão da integração Google. Não porque isso seja chique, mas porque lembrete que só existe no app do Google e some do briefing é um tipo bem específico de burrice.
- Nova coleta de tarefas do dia via `Tasks API`, anexada ao snapshot direto quando o perfil já tiver o escopo necessário.
- Novos testes unitários cobrindo a coleta de tarefas do dia e o comportamento do snapshot com e sem `tasks.readonly`.

### Changed
- O `snapshot-refresh` agora acusa explicitamente quando `Tasks API` ainda não está conectada no perfil ativo, em vez de fingir que a agenda está completa.
- A agenda do briefing passa a incluir tarefas/lembretes do Google quando a integração estiver reautenticada com o escopo novo.

### Fixed
- A ausência de `Tasks API` deixou de derrubar ou confundir a integração inteira. Agora vira aviso claro, não apagão operacional.

## [4.11.3] - 2026-03-20

### Changed
- A heurística de `sinal fraco` saiu do cabo de guerra entre `briefing.py` e `google_api.py` e passou a morar num lugar só. Menos chance de uma regra dizer “isso é ruído” enquanto a outra pede casamento.
- A linha `Google:` do briefing agora mostra idade relativa do último refresh (`17h38 atrás`), em vez de exigir que o usuário faça conta de cabeça como se estivesse em prova de regra de três.
- A seção `Emails` passou a separar melhor mensagem para gente e nota interna. O produto continua honesto, mas parou de soar como stack trace com boas maneiras.
- O cache de agenda/snapshot também ganhou idade relativa humana no texto, porque `1057 min atrás` é linguagem de torno mecânico, não de produto.

### Fixed
- O smoke de Calendar/Gmail foi alinhado ao contrato novo do briefing e deixou de falhar por maiúscula ornamental.

## [4.11.2] - 2026-03-19

### Added
- O briefing local agora mostra explicitamente o estado da integração Google, a conta ativa e o último refresh útil.
- Quando o refresh token do Google azeda, o runtime marca o perfil como `needs_reauth` em vez de deixar a falha virar neblina.

### Changed
- A seção `Emails` do briefing passou a dizer `Nenhum email novo...` quando a Gmail API vier limpa. Silêncio com cara de bug foi demitido.
- O briefing passou a indicar o caminho de reauth (`prumo auth google --workspace ...`) quando a integração Google precisar ser refeita.
- Os smokes do runtime/bridge foram alinhados ao briefing com bloco explícito `Google`.

## [4.11.1] - 2026-03-19

### Added
- `prumo auth google` agora aceita `--client-id` e `--client-secret` diretamente, sem obrigar o usuário a caçar JSON no labirinto do Google Cloud.
- Novo teste unitário `runtime/tests/test_auth_google.py` cobrindo resolução de credenciais por flags e por arquivo.

### Changed
- `.gitignore` agora ignora `_secrets/`, `client_secret*.json`, `credentials*.json` e afins. Segredo em repositório é só autobiografia do desastre.
- A proposta do dia do briefing deixou de tratar email banal de billing/upgrade como bússola moral quando já existe trabalho real na pauta.
- A triagem Gmail ganhou um pouco mais de faro: assunto com cheiro de ação sobe para `P1`; notificação burocrática evidente cai para ruído.

## [4.11.0] - 2026-03-19

### Added
- `snapshot-refresh` passou a usar Google Calendar API e Gmail API diretas quando houver conta conectada no runtime.
- Novo smoke `local_runtime_google_calendar_smoke.sh` cobrindo refresh direto via Google APIs fake locais, com agenda e email.
- Nova suíte unitária em `runtime/tests/` cobrindo parser Google, estado da integração e fallback/cache do briefing local.

### Changed
- O briefing agora prefere cache abastecido por Google APIs diretas quando ele existir, sem perder o fallback anterior quando a fonte nova tropeçar.
- A triagem de email via Gmail API entra de forma conservadora. Melhor modéstia operacional do que teatro com prioridade inventada.

## [4.10.0] - 2026-03-19
### Added
- Novo comando `prumo auth google` para conectar a conta Google via navegador, sem depender de host externo como atravessador.
- Novo arquivo derivado `_state/google-integration.json` para guardar estado e metadado da integração Google dentro do workspace.

### Changed
- `prumo context-dump` agora expõe o estado da integração Google, o perfil ativo e os perfis conectados, em vez de tratar isso como segredo de porão.
- `setup`, `migrate` e `repair` passam a materializar e reconstruir `_state/google-integration.json` quando necessário.
- O runtime, no macOS, passa a guardar token sensível no Keychain em vez de largar credencial em texto puro no workspace.

## [4.9.5] - 2026-03-19

### Added
- `prumo snapshot-refresh` agora aceita `--profile pessoal|trabalho`, para refresh explícito sem arrastar a outra conta junto.

### Changed
- O experimento de resgate automático por perfil/escopo foi descartado. Parecia resiliente no papel e só alongou o sofrimento no runtime real.
- `EXECUTION-NOTES.md` passou a registrar explicitamente que agenda e email, mesmo isolados no perfil pessoal, continuam expirando no caminho atual Gemini+MCP.
- A Fase 1 assume `pessoal` como perfil Google padrão. Multi-conta sai do caminho por enquanto.
- Nova decisão arquitetural formalizada em [ADR-001-GOOGLE-INTEGRATION.md](ADR-001-GOOGLE-INTEGRATION.md): integração Google do runtime segue para Google APIs diretas; snapshots ficam como ponte/fallback.

## [4.9.4] - 2026-03-19

### Added
- Novo `EXECUTION-NOTES.md` para registrar descobertas tecnicas que realmente mudam direcao. Nem amnesia de sessao, nem ata de condomínio.

### Changed
- O `snapshot-refresh` e o shell script dual deixaram de fazer um auth check textual redundante no Gemini antes de consultar o MCP.
- A coleta dual agora roda os perfis em paralelo, porque esperar um de cada vez era um jeito bem elaborado de chamar lentidao de prudencia.
- A janela de timeout do refresh explicito ficou um pouco mais realista para esse fluxo externo, sem transformar o briefing em retiro espiritual.
- Quando o refresh estoura no meio, o runtime agora tenta preservar resultado parcial util em vez de jogar fora o que ja chegou.

## [4.9.3] - 2026-03-19

### Added
- Novo comando `prumo snapshot-refresh` para atualizar explicitamente o cache local de agenda/email antes do briefing. O produto parou de fingir que supermercado e geladeira são a mesma coisa.

### Changed
- O `prumo briefing` agora prefere o cache local de snapshot dual por padrão e só depende de refresh ao vivo quando isso for explicitamente pedido ou necessário.

## [4.9.2] - 2026-03-19

### Changed
- O `prumo briefing` ganhou cache local de snapshot dual em `_state/google-dual-snapshot.json`. Se a coleta ao vivo funcionar uma vez, o runtime passa a ter memória curta decente em vez de amnésia performática.
- Quando o snapshot ao vivo falha, expira ou é desligado por ambiente, o briefing agora reaproveita cache válido e avisa isso explicitamente na agenda e na triagem de emails.
- O smoke da Fase 1 passou a verificar também o reaproveitamento do cache, porque integração externa temperamental sem teste vira superstição com shell.

## [4.9.1] - 2026-03-19

### Changed
- O `prumo briefing` do runtime local deixou de ser só um leitor tímido de `PAUTA.md`. Agora ele tenta gerar preview de `Inbox4Mobile`, reaproveita `_preview-index.json`, tenta o snapshot dual com timeout curto e organiza o panorama em blocos mais próximos do briefing real.
- O fallback do snapshot dual ficou civilizado: se o script demorar, o briefing o abandona sem transformar a manhã do usuário em retiro espiritual.
- O módulo `runtime-paths.md` agora deixa explícito que `scripts/prumo_google_dual_snapshot.sh` pode existir como artefato gerado no workspace enquanto o repo guarda o template/fallback em `references/`.

### Added
- O smoke `local_runtime_phase1_smoke.sh` agora cobre agenda via snapshot fake, preview de inbox e saída com opções `a)` a `d)` no briefing local.

## [4.9.0] - 2026-03-19

### Added
- Novo comando `prumo migrate` para adotar workspace legado no trilho novo com backup antes de tocar em wrapper e core.
- Novo smoke `cowork-plugin/scripts/tests/local_runtime_migrate_smoke.sh` cobrindo backup, import do `CLAUDE.md` legado e atualização segura do `PRUMO-CORE.md`.

### Changed
- A trilha mínima de migração da Fase 1 deixou de ser implícita. Agora o produto tem um comando claro para isso, em vez de empurrar toda a responsabilidade para um `setup` excessivamente educado.
- Migração de workspace legado passa a preservar o `CLAUDE.md` antigo em `Agente/LEGADO-CLAUDE.md`, o que é muito melhor do que chamar perda de contexto de “compatibilidade”.

## [4.8.1] - 2026-03-19

### Added
- Novo `scripts/prumo_cowork_bridge.py` como bridge experimental entre Cowork e o runtime local.
- Novo smoke `cowork-plugin/scripts/tests/cowork_runtime_bridge_smoke.sh` cobrindo o caminho feliz do bridge e o fallback silencioso para workspace legado.
- Novo módulo canônico `cowork-runtime-bridge.md` para tirar essa lógica do campo da telepatia.

### Changed
- O `/briefing` no Cowork agora deve tentar o runtime local primeiro quando o workspace já estiver no trilho novo (`AGENT.md` + `_state/workspace-schema.json`) e houver shell.
- Se o bridge funcionar, o Cowork devolve a saída do runtime e encerra. Se não, cai para o fluxo legado sem chilique.
- `.gitignore` deixou de esconder scripts oficiais novos como se release fosse contrabando.

## [4.8.0] - 2026-03-19

### Added
- Runtime local experimental em `runtime/prumo_runtime/`, com CLI inicial e package Python.
- Primeiros comandos do novo trilho:
  - `prumo setup`
  - `prumo briefing`
  - `prumo context-dump`
  - `prumo repair`
- Novo smoke `cowork-plugin/scripts/tests/local_runtime_phase1_smoke.sh` para validar setup, schema, wrappers regeneráveis, context-dump e briefing mínimo.
- Scripts de bootstrap do runtime:
  - `scripts/prumo_runtime_install.sh`
  - `scripts/prumo_runtime_update.sh`
- Novo plano cirúrgico da Fase 1 em `LOCAL-RUNTIME-PHASE1-PLAN.md`.

### Changed
- O plano de transição foi consolidado após validação cruzada de Cowork e Gemini:
  - `AGENT.md` agora é o índice canônico do workspace;
  - `CLAUDE.md` e `AGENTS.md` viram wrappers regeneráveis;
  - `Agente/` vira o diretório modular de contexto do usuário;
  - setup didático, no-lock-in explícito e contrato de documentação local entram como parte formal do produto.
- `PRUMO-CORE.md` subiu para `4.8.0` para parar de nascer defasado quando o runtime novo o materializa no workspace.

### Fixed
- O primeiro smoke do runtime pegou um conflito chato e real: o `PRUMO-CORE.md` gerado estava nascendo com versão anterior ao runtime. Isso já saiu corrigido antes do commit, em vez de virar presente envenenado para o primeiro usuário.

## [4.7.3] - 2026-03-19

### Fixed
- O briefing voltou a tratar update como preflight de verdade, não como leitura opcional de módulo esquecida no canto.
- Quando houver versão nova detectável, o briefing agora deve avisar antes do panorama e oferecer alternativas curtas (`atualizar agora`, `seguir mesmo assim`, `ver diagnóstico`).
- Regressão pública rastreada em [#38](https://github.com/tharso/prumo/issues/38).

## [4.7.2] - 2026-03-19

### Fixed
- O briefing agora distingue `motor do workspace defasado` de `release inconsistente`. No caso real do `DailyLife`, `PRUMO-CORE.md` velho ao lado de `Prumo/VERSION` novo passa a ser tratado como drift operacional explícito.
- O preflight do briefing deve acusar esse drift antes do panorama, em vez de fingir normalidade e depois tropeçar em regra antiga.
- Regressão pública rastreada em [#39](https://github.com/tharso/prumo/issues/39).

## [4.7.1] - 2026-03-19

### Added
- Novo módulo canônico [interaction-format.md](cowork-plugin/skills/prumo/references/modules/interaction-format.md) definindo o contrato de interface do Prumo no chat: numeração contínua durante o mesmo fluxo e alternativas curtas quando houver mais de um caminho razoável.
- Novo smoke [interaction_contract_smoke.sh](cowork-plugin/scripts/tests/interaction_contract_smoke.sh) para evitar que essa diretriz volte a virar folclore enterrado em um módulo só.
- Issue pública da regressão: [#37](https://github.com/tharso/prumo/issues/37).

### Changed
- `PRUMO-CORE.md` agora trata continuidade de numeração e oferta de alternativas como regras estáveis do sistema, não como hábito local do briefing.
- `briefing`, `handover`, `higiene`, `doctor` e `start` foram reforçados para responder com continuidade de fluxo e reduzir atrito de resposta do usuário.

## [4.7.0] - 2026-03-18

### Added
- Novo `scripts/prumo_cowork_doctor.sh` para diagnosticar o store real do Cowork, checkout do marketplace, versão instalada, drift de catálogo e o caso clássico do botão `Atualizar` morrer enquanto o checkout local continua preso no passado.
- Novo `scripts/prumo_cowork_update.sh` para atualizar os checkouts do marketplace do Prumo usados pelo Cowork e renovar o timestamp de sync sem sair remendando o cache do plugin na marra.
- Novo comando `/doctor` e skill dedicada para expor esse diagnóstico no próprio produto.
- Novo módulo canônico [cowork-runtime-maintenance.md](cowork-plugin/skills/prumo/references/modules/cowork-runtime-maintenance.md) consolidando a política de instalação e update no Cowork.
- Novo smoke [cowork_runtime_smoke.sh](cowork-plugin/scripts/tests/cowork_runtime_smoke.sh) para validar o caso de catálogo congelado em store fake.

### Changed
- O caminho recomendado para instalar o Prumo no Cowork agora é o repositório Git `https://github.com/tharso/prumo.git`, não a URL `raw` do marketplace.
- `prumo_plugin_install.sh` deixou de fingir que resolve sozinho o store local do Cowork e passou a apontar explicitamente para os scripts de `doctor` e `update` quando a UI congelar.
- README, playbook e comando `doctor` agora tratam o botão `Atualizar` como sinal fraco. A verdade mora no store local, não no teatro do painel.

### Fixed
- O produto ganhou um trilho canônico para diagnosticar e corrigir catálogo congelado no Cowork. Usuário não deveria precisar virar arqueólogo de cache para instalar release nova.

## [4.6.3] - 2026-03-18

### Changed
- `Mudanças seguras` em `/higiene` agora é um bloco realmente disciplinado: só entra ali o que o patch atual consegue aplicar sem escolha semântica.
- O relatório passou a avisar explicitamente quando o `PRUMO-CORE.md` do workspace está defasado em relação ao runtime.
- JSON e Markdown de higiene agora mostram com clareza quando um item é autoaplicável e quando é só diagnóstico de governança.

## [4.6.2] - 2026-03-18

### Changed
- O relatório e a skill de `/higiene` agora separam explicitamente a proposta em 3 blocos fixos:
  - `Mudanças seguras`
  - `Itens que pedem confirmação factual`
  - `Decisões de governança/arquitetura`
- O produto deixa de depender de prompt manual do usuário para distinguir limpeza estrutural, verdade factual pendente e decisão de arquitetura do arquivo.

## [4.6.0] - 2026-03-18

### Added
- Novo módulo canônico [runtime-file-governance.md](cowork-plugin/skills/prumo/references/modules/runtime-file-governance.md) definindo o contrato de permanência entre `CLAUDE.md`, `PAUTA.md`, `REGISTRO.md` e histórico.
- A higiene assistida agora classifica drift de conteúdo em `CLAUDE.md`, incluindo:
  - lembretes vencidos;
  - histórico/changelog no arquivo vivo;
  - status transitórios envelhecidos;
  - destino sugerido por achado.
- Issue pública da feature: [#35](https://github.com/tharso/prumo/issues/35).

### Changed
- `/higiene` deixou de ser só “detector de duplicação” e passou a agir como primeira camada de governança do arquivo vivo do usuário.
- `claude-md-template.md` agora explicita que lembrete datado não mora em `CLAUDE.md`.
- Smoke de higiene reforçado para validar destinos sugeridos e garantir que itens com confirmação factual não sejam auto-removidos.

### Fixed
- Versionamento do plugin/manifests alinhado para `4.6.0`. Já bastava de painel contando uma história e arquivo contando outra.

## [4.6.1] - 2026-03-18

### Fixed
- A heurística de `historical_record` em `prumo_claude_hygiene.py` ficou menos afoita: sem heading contextual, agora ela exige pelo menos duas linhas com cara de changelog antes de classificar um bloco como histórico deslocado.
- O smoke de higiene passou a cobrir explicitamente `transient_status` e um caso negativo para reduzir risco de falso positivo. Governança de arquivo não pode sair vendo fantasma em aniversário antigo.

## [4.5.1] - 2026-03-18

### Added
- Novo instalador/atualizador canônico em [scripts/prumo_plugin_install.sh](scripts/prumo_plugin_install.sh) para adicionar o marketplace e instalar/atualizar o plugin pelo CLI do Claude/Cowork.

### Changed
- README agora trata o fluxo por CLI como caminho preferencial para instalação/update do Prumo e documenta a UI de marketplace como caminho secundário, porque fingir que ela é sempre confiável seria publicidade enganosa com cara de tutorial.
- Playbook e protocolo de release reforçam que a atualização do plugin precisa ser validada pelo backend, não só por um toast simpático da UI.

## [4.5.2] - 2026-03-18

### Fixed
- Documentação e comandos agora refletem o comportamento real do Cowork: os slash commands do Prumo aparecem sem prefixo de plugin (`/setup`, `/briefing`, `/handover`, `/sanitize`, `/higiene`, `/start`).
- O produto deixou de sugerir `/prumo:*` como caminho canônico no Cowork, porque promessa falsa com cara de alias é só bug usando gravata.

## [4.5.3] - 2026-03-18

### Fixed
- `plugin.json` e `.claude-plugin/plugin.json` voltaram a declarar explicitamente as skills do Prumo. Sem isso, o Cowork recebia metadado de plugin mas não tinha o que carregar, que é uma forma bem elaborada de instalar nada.

## [4.5.0] - 2026-03-16

### Added
- Novo comando `/prumo:higiene` para revisão assistida do `CLAUDE.md`, separado de `sanitize`.
- Novo script `cowork-plugin/scripts/prumo_claude_hygiene.py` que:
  - diagnostica duplicações, redundâncias e conflitos potenciais;
  - gera relatório JSON/Markdown;
  - gera patch proposto;
  - só aplica com `--apply`, criando backup e registrando em `REGISTRO.md`.
- Novo módulo canônico [claude-hygiene.md](cowork-plugin/skills/prumo/references/modules/claude-hygiene.md) e nova skill dedicada [higiene/SKILL.md](cowork-plugin/skills/higiene/SKILL.md).
- Smoke dedicado `cowork-plugin/scripts/tests/claude_hygiene_smoke.sh`.
- Issue pública da feature: [#33](https://github.com/tharso/prumo/issues/33).

### Changed
- `PRUMO-CORE.md`, README, setup e regras de proteção agora deixam explícito que `CLAUDE.md` é configuração viva e não participa de autosanitização.
- `sanitize` passou a apontar explicitamente para `/prumo:higiene` quando a demanda for limpeza do `CLAUDE.md`.
- Versionamento sincronizado para `4.5.0` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`

## [4.4.1] - 2026-03-16

### Fixed
- `prumo-core.md` voltou a ficar coerente consigo mesmo: header, rodapé e bloco de versão agora apontam para a mesma release.
- Smokes deixaram de depender de `rg --pcre2`, que em alguns runtimes existe sem suporte PCRE2 e falhava por vaidade técnica, não por bug real da feature.

## [4.4.0] - 2026-03-16

### Added
- Novo script `cowork-plugin/scripts/prumo_archive_cold_files.py` para archive conservador de arquivos frios em `Inbox4Mobile/`, com suporte a dry-run, thresholds configuráveis e refresh do preview após movimentação.
- Novo helper `cowork-plugin/scripts/prumo_archive_index.py` para manter o índice global de archive em:
  - `_state/archive/ARCHIVE-INDEX.json`
  - `_state/archive/ARCHIVE-INDEX.md`
- Template explícito para `Inbox4Mobile/_processed.json` e documentação do contrato mínimo usado pela autolimpeza.
- Nova issue pública para a feature: [#32](https://github.com/tharso/prumo/issues/32).

### Changed
- `prumo_sanitize_state.py` agora registra compactação de handovers no índice global de archive, em vez de só mover texto para `HANDOVER-ARCHIVE.md`.
- `prumo_auto_sanitize.py` ganhou terceiro eixo de manutenção: detecção e archive de arquivos processados e frios do inbox, com telemetria de candidatos e bytes acumulados.
- Core, módulo de sanitização, módulo de inbox e runtime paths atualizados para explicitar guardrails de archive e a nova política conservadora.
- Versionamento sincronizado para `4.4.0` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`

### Fixed
- Sanitização deixa de ser um mecanismo parcial sem índice global; agora todo movimento suportado precisa deixar rastro consultável.

## [4.3.1] - 2026-03-16

### Fixed
- `cowork-plugin/skills/briefing/SKILL.md` foi limpo de um bloco residual quebrado que ainda deixava texto renderizado como código.
- Novo módulo `cowork-plugin/skills/prumo/references/modules/runtime-paths.md` centraliza `SCRIPT_PATHS` e a lista de scripts oficiais do runtime.
- Módulos que dependem de shell agora apontam para `runtime-paths.md`, em vez de deixar a resolução de paths implícita ou espalhada.
- Regra de feedback do produto voltou a aparecer explicitamente no core, com ponteiro para `feedback-loop.md`.
- Smoke test reforçado para validar `runtime-paths`, regra de feedback e ausência de resíduo quebrado no briefing skill.

## [4.3.0] - 2026-03-16

### Changed
- `PRUMO-CORE.md` foi refatorado para um core enxuto com regras estáveis, mapa de módulos e guardrails explícitos em `ASSERT:`.
- Procedimentos detalhados passaram para módulos canônicos em `cowork-plugin/skills/prumo/references/modules/`.
- `cowork-plugin/skills/briefing/SKILL.md` deixou de duplicar o briefing inteiro e passou a carregar o módulo canônico.
- `cowork-plugin/skills/briefing/references/briefing-fast-path.md` e `load-policy.md` viraram ponteiros para os módulos canônicos, em vez de manter fonte paralela.
- Smoke test atualizado para validar modularização, presença de `ASSERT:` e ausência de changelog inline no core.

## [4.2.5] - 2026-03-16

### Changed
- Snapshots multi-conta deixam de ser gravados como `email-snapshot.json` bruto no Drive e passam a ser gravados como Google Docs com JSON texto em `Prumo/snapshots/email-snapshot`.
- Ajuste motivado por limitação validada em runtime: o MCP de Google Drive do Cowork consegue ler Google Docs, mas não JSON bruto com confiabilidade suficiente para o briefing.
- Briefing, setup e core atualizados para procurar o Google Doc, ler o texto e parsear o JSON antes de cair para fallbacks.
- Templates dos Apps Scripts atualizados para criar/atualizar Google Docs em vez de arquivos texto puros.
- Versionamento sincronizado para `4.2.5` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`
- Smoke test de briefing reforçado para validar referência a Google Docs no contrato de snapshots.

## [4.2.4] - 2026-03-16

### Added
- Briefing passa a priorizar snapshots privados `Prumo/snapshots/email-snapshot.json` no Google Drive como fonte multi-conta para agenda e emails.
- Guia operacional em `docs/apps-script-setup.md` atualizado com o contrato de consumo do briefing.

### Changed
- Setup do Prumo passa a recomendar Google Apps Script + Google Drive como caminho preferencial para email/calendar multi-conta, deixando Gemini dual como fallback avançado.
- Core e skill de briefing agora exigem:
  - alerta explícito quando `generated_at` estiver acima de 30 minutos;
  - tolerância a falha parcial com `emails_error` e `calendar_error`;
  - timeout de 45 segundos na leitura dos snapshots antes de cair para fallback.
- Versionamento sincronizado para `4.2.4` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`
- Smoke test de briefing reforçado para validar a presença do contrato de snapshots no Drive.

## [4.2.3] - 2026-03-16

### Fixed
- Persistência do briefing movida para o início da sessão, antes da primeira resposta, para evitar falso “X dias sem briefing” quando o usuário acabou de rodar a rotina no dia anterior.
- A janela temporal da sessão agora usa o valor anterior de `last_briefing_at`, capturado em memória antes da nova gravação.

### Added
- Helper `cowork-plugin/scripts/prumo_briefing_state.py` para persistir início, conclusão e interrupção do briefing quando houver shell.

### Changed
- Versionamento sincronizado para `4.2.3` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`
- Smoke test de briefing reforçado para validar gravação no início da sessão e presença do helper de estado.

## [4.2.2] - 2026-03-16

### Fixed
- O aviso de atualização deixa de buscar changelog remoto via WebFetch só para enriquecer a mensagem.
- Quando não houver changelog acessível por fonte local segura, o Prumo anuncia a nova versão sem detalhes em vez de depender de leitura web interpretada.

### Changed
- Versionamento sincronizado para `4.2.2` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`
- Smoke test de briefing reforçado para validar fallback sem changelog remoto no fluxo de update.

## [4.2.1] - 2026-03-16

### Fixed
- Auto-update do core reescrito para separar detecção de versão de aplicação da atualização.
- WebFetch/leitura remota resumida passam a ser tratadas como fonte inválida para sobrescrever `PRUMO-CORE.md`.
- Quando o runtime só consegue comparar `VERSION`, o Prumo informa a limitação e não bloqueia mais o briefing com uma atualização impossível de aplicar.

### Changed
- Aplicação automática do core fica restrita a fonte local bruta ou updater via shell.
- Versionamento sincronizado para `4.2.1` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`
- Smoke test de briefing reforçado para validar a proibição de WebFetch como fonte de update e a distinção entre detectar e aplicar atualização.

## [4.2.0] - 2026-03-16

### Fixed
- Persistência de briefing corrigida: fechamento não depende mais do `prumo_google_dual_snapshot.sh` para gravar `_state/briefing-state.json`.
- Contrato de persistência alinhado entre core e skill de briefing, com validação distinta para briefing concluído e briefing interrompido.
- `cowork-plugin/scripts/safe_core_update.sh` atualizado para buscar o core no path remoto atual e abortar quando o arquivo remoto vier truncado ou incompleto.

### Changed
- Versionamento sincronizado para `4.2.0` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`
- Smoke test de briefing reforçado para validar consistência da superfície pública da release e o novo contrato de persistência.

## [4.1.1] - 2026-03-10

### Changed
- Removida a chave `skills` dos manifests `plugin.json` e `.claude-plugin/plugin.json` para validar descoberta de comandos/skills via fluxo atual do Cowork, sem alterar a estrutura física de diretórios.
- Versionamento sincronizado para `4.1.1` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`

## [4.1.0] - 2026-03-03

### Added
- Diretório `commands/` no plugin com slash commands explícitos para UI do Cowork:
  - `commands/setup.md`
  - `commands/prumo.md` (alias legado)
  - `commands/briefing.md`
  - `commands/handover.md`
  - `commands/sanitize.md`
  - `commands/start.md`
- Comando legado `/prumo:prumo` preservado via alias dedicado, sem quebrar fluxo de usuários existentes.

### Changed
- Versionamento sincronizado para `4.1.0` em:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json`
  - `.claude-plugin/plugin.json`
  - `marketplace.json`
  - `.claude-plugin/marketplace.json`
- README atualizado para refletir `/prumo:setup` como comando canônico e `/prumo:prumo` como alias legado.

## [4.0.5] - 2026-02-27

### Fixed
- Corrigidos comandos de manutenção no briefing/sanitize para suportar layout atual do workspace:
  - `scripts/*` (workspace local)
  - `Prumo/cowork-plugin/scripts/*` (layout atual do repo Prumo no workspace)
  - `Prumo/scripts/*` (fallback legado)
- Corrigido caminho remoto/local usado na checagem de update do core no briefing:
  - remoto: `.../cowork-plugin/skills/prumo/references/prumo-core.md`
  - fallback local: `Prumo/cowork-plugin/skills/prumo/references/prumo-core.md` (com fallback legado mantido).
- Referências de execução (`briefing-fast-path`, `sanitize`, `prumo-core`) alinhadas para evitar erro `python3: can't open file` em instalações via marketplace.

## [4.0.4] - 2026-02-27

### Fixed
- Hardening para discovery de slash command no Cowork Desktop:
  - removido `cowork-plugin/plugin.json` para eliminar manifesto duplicado no pacote distribuído.
  - mantido um único contrato de plugin de distribuição (`plugin.json` na raiz e cópia em `.claude-plugin/plugin.json`).
- Versão sincronizada para forçar refresh limpo de cache no update via marketplace.

## [4.0.3] - 2026-02-27

### Fixed
- Conflito de manifest no loader de plugins do Cowork resolvido:
  - `marketplace.json` agora usa `strict: true` no entry do plugin.
  - definição de skills migrou para `plugin.json` (raiz e `.claude-plugin/plugin.json`), evitando dupla origem de componentes.
- `cowork-plugin/plugin.json` atualizado com skills explícitas para manter paridade com instalação por pacote local.

## [4.0.2] - 2026-02-27

### Fixed
- Fluxo de instalação via marketplace por URL (`raw`) ajustado para não depender de `source` relativo no cache local.
- `source` do plugin no marketplace agora usa fetch Git explícito (`https://github.com/tharso/prumo.git` + `ref: main`) com `strict: false` e skills declaradas.
- `marketplace.name` alterado para `prumo-marketplace` para evitar recursão de cache no instalador quando slug do marketplace e slug do plugin são idênticos.

### Added
- Manifestos em `.claude-plugin/` (`marketplace.json` e `plugin.json`) para compatibilidade com adição de marketplace por URL de repositório `.git`.

## [4.0.1] - 2026-02-27

### Changed
- Repositório público sanitizado para distribuição: remoção de artefatos internos de desenvolvimento e operação.
- Fonte do marketplace consolidada para `./cowork-plugin` (pacote enxuto e orientado a runtime).
- Metadados públicos dos manifests ajustados para reduzir exposição de dados pessoais.

### Removed
- Estruturas internas de engenharia no repositório público: `.github/`, `.claude-plugin/`, `docs/`, `scripts/`, `skills/` e `prumo-landing-v2.html`.

## [4.0.0] - 2026-02-26

### Changed
- Reorganização estrutural das skills para o padrão de plugin do Cowork: `skills/<nome>/SKILL.md`.
- Skill de setup (`skills/prumo/SKILL.md`) refatorada com progressive discovery (conteúdo de suporte movido para `skills/prumo/references/`).
- Referências modulares de briefing e sanitização movidas para dentro das respectivas skills (`skills/briefing/references/` e `skills/sanitize/references/`).

### Added
- Estrutura de plugin no repositório em `.claude-plugin/plugin.json` e `.claude-plugin/marketplace.json`.
- Nova skill de onboarding dump-first em `skills/start/SKILL.md`.
- Referências dedicadas do setup: `feedback-loop.md`, `file-protection-rules.md` e `changelog-setup.md`.

### Removed
- Arquivos legados/duplicados na raiz: `SKILL.md`, `skills-briefing-SKILL.md`, `skills-handover-SKILL.md` e `skills-sanitize-SKILL.md`.

### Fixed
- Correções de paths em `skills/briefing/SKILL.md`, `skills/sanitize/SKILL.md` e `skills/start/SKILL.md` após a migração de estrutura.

## [3.8.3] - 2026-02-23

### Fixed
- `scripts/generate_inbox_preview.py` agora degrada preview de YouTube em `file://` para fallback seguro (thumbnail + link), evitando iframe quebrado com erro 153.
- Corrigido bug de interpolação no HTML/JS gerado (`NameError` em `safeWatch`/`safeThumb`) que podia abortar a geração do `inbox-preview.html`.

### Added
- Regressão no smoke test para garantir presença do fallback de YouTube local (`location.protocol === 'file:'` + `yt-fallback-caption`) no HTML gerado.

## [3.8.2] - 2026-02-23

### Fixed
- `scripts/generate_inbox_preview.py` corrigido para resolver `--index-output` relativo como path independente de `--output`.
- Evita path duplicado em chamadas relativas (caso clássico: `Inbox4Mobile/Inbox4Mobile/_preview-index.json`).
- Comandos documentados do briefing ajustados para usar `--index-output Inbox4Mobile/_preview-index.json` explicitamente.

### Added
- Regressão automatizada no smoke test para garantir que `--index-output` relativo não seja concatenado ao diretório de `--output`.

## [3.8.1] - 2026-02-23

### Fixed
- Hardening da adoção de preview no briefing para reduzir falha de compliance do agente:
  - preview de inbox passa a ser regenerado no início do briefing (quando shell disponível),
  - primeira interação do briefing não pode abrir arquivo bruto de `Inbox4Mobile/*`.
- Quando a regeneração falha mas já existe preview anterior, o fluxo agora exige linkar o preview mesmo assim, com aviso de possível defasagem.

### Changed
- Core e skills de briefing atualizados com guardrail explícito de ordem (panorama/proposta antes de abertura individual).
- Smoke test reforçado para validar regeneração de preview e bloqueio de abertura bruta na primeira interação.

## [3.8.0] - 2026-02-23

### Added
- Briefing progressivo em dois blocos no core/skills:
  - Bloco 1 automático (agenda + preview inbox + contagem silenciosa de agendados),
  - Bloco 2 com interação única (`a/b/c/d`) e contexto completo sob demanda (`--detalhe`).
- Escape hatch no briefing com estado persistido em `_state/briefing-state.json`:
  - `interrupted_at`
  - `resume_point`
- Supressão temporal para agendados com formato `| cobrar: DD/MM` (ou `DD/MM/AAAA`).

### Changed
- Regra 14 do core reestruturada para briefing progressivo (substitui modelo de dump integral).
- Revisão semanal explicitamente preservada como visão completa (sem supressão por cobrança).
- Template de `PAUTA.md` e template de `_state/briefing-state.json` atualizados com o novo contrato.
- Smoke test de briefing reforçado para validar blocos, escape e semântica de cobrança.

## [3.7.6] - 2026-02-22

### Fixed
- Alinhamento de versão entre `VERSION` e `references/prumo-core.md` (`prumo_version`), eliminando divergência no aviso de update do briefing.
- Changelog interno do core sincronizado para incluir `v3.7.4` e `v3.7.5`, evitando mensagem de "versão remota maior sem changelog correspondente".

### Changed
- Fluxo de update no core/skills agora trata fonte remota incompleta (arquivo truncado sem seção de changelog/rodapé) como inválida e cai para fallback local.
- CI ganhou guardrail de consistência entre `VERSION`, `prumo_version` e seção correspondente no `Changelog do Core`.

## [3.7.5] - 2026-02-22

### Changed
- Adoção de preview no briefing endurecida como regra bloqueante no core e nas skills:
  - se `Inbox4Mobile/_preview-index.json` existir, o agente deve linkar `Inbox4Mobile/inbox-preview.html` antes de abrir arquivos individuais;
  - abertura de arquivo bruto antes do preview só é válida em falha objetiva de geração/leitura.
- Fallback de triagem agora exige explicitar no briefing quando houve falha de preview.

### Added
- Smoke test de briefing reforçado para validar regra de adoção do preview (presença explícita de `_preview-index.json` e obrigação de linkar `inbox-preview.html`).

## [3.7.4] - 2026-02-22

### Fixed
- `scripts/tests/briefing_smoke.sh` agora faz fallback para `grep` quando `rg` não está disponível no runner, evitando falso negativo no CI.

## [3.7.3] - 2026-02-22

### Added
- Workflow de release automatizada em `.github/workflows/release.yml`:
  - valida `VERSION` em semver,
  - valida entrada correspondente no `CHANGELOG.md`,
  - cria tag `vX.Y.Z` quando ausente,
  - cria/atualiza GitHub Release com notas extraídas do changelog.
- Smoke test de briefing em `scripts/tests/briefing_smoke.sh` cobrindo:
  - taxonomia `Responder`/`Ver`/`Sem ação`,
  - prioridade `P1/P2/P3`,
  - janela temporal (`last_briefing_at` + fallback 24h),
  - paridade de instruções para runtime com shell e sem shell.
- Script `scripts/github/sync_project_schema.sh` para sincronizar schema/valores do Project existente.

### Changed
- CI (`.github/workflows/ci.yml`) passa a executar smoke tests de briefing.
- Bootstrap de project (`scripts/github/bootstrap_project.sh`) agora aplica schema automaticamente e deixa checklist explícito de views no README do board.
- `scripts/github/sync_project_schema.sh` ajustado para compatibilidade com Bash do macOS (sem dependência de Bash 4+).
- Documentação (`README.md`, `docs/WORKFLOW.md`) atualizada para refletir release automática, smoke tests e sync de schema.

## [3.7.2] - 2026-02-22

### Added
- Histórico local de autosanitização por workspace em `_state/auto-sanitize-history.json`.
- Estado de autosanitização expandido com modo adaptativo, thresholds efetivos e overrides.

### Changed
- `scripts/prumo_auto_sanitize.py` agora calibra thresholds por usuário/workspace (quando há amostra suficiente), com fallback seguro para defaults.
- Documentação (`docs/AUTOSANITIZACAO.md`, `README.md`, módulos de referência e core) atualizada para explicitar calibração por usuário, não por média global.

## [3.7.1] - 2026-02-22

### Added
- Script `scripts/prumo_auto_sanitize.py` para autosanitização por gatilhos com cooldown.
- Estado persistido de manutenção em `_state/auto-sanitize-state.json` (métricas, decisão e ações).

### Changed
- Core (`references/prumo-core.md`) evoluiu para `3.7.1` com regra formal de autosanitização.
- Skills de briefing agora podem executar autosanitização preventiva (best-effort, sem bloquear briefing).
- Documentação de sanitização e política de leitura incremental atualizadas para incluir fluxo automático.

## [3.7.0] - 2026-02-22

### Added
- Script `scripts/prumo_sanitize_state.py` para compactar `HANDOVER` sem perda de histórico:
  - move `CLOSED` antigos para `_state/archive/HANDOVER-ARCHIVE.md`,
  - gera backup em `_state/archive/backups/`,
  - gera `_state/HANDOVER.summary.md` para leitura leve.
- Módulos de leitura incremental:
  - `references/modules/load-policy.md`
  - `references/modules/briefing-fast-path.md`
  - `references/modules/sanitization.md`
- Skill operacional `/prumo:sanitize` (`skills/sanitize/SKILL.md` e `skills-sanitize-SKILL.md`).

### Changed
- Briefing oficializado em dois estágios para inbox multimídia:
  - Estágio A (triagem leve): preview + índice (`inbox-preview.html` + `_preview-index.json`);
  - Estágio B (aprofundamento seletivo): abrir bruto só para `P1`, ambíguos ou itens de risco.
- `scripts/generate_inbox_preview.py` atualizado:
  - corrige caminhos relativos quando o HTML é salvo dentro de `Inbox4Mobile/`,
  - exclui os arquivos gerados da própria listagem,
  - ordena do mais recente para o mais antigo,
  - remove inline base64 de imagem para reduzir peso do HTML.
- Core e skills de briefing atualizados para priorizar leitura leve e reduzir overhead de contexto.

## [3.6.7] - 2026-02-22

### Changed
- Hardening da abertura de briefing para evitar data errada por UTC:
  - dia/data só podem ser anunciados com fonte de tempo verificável no fuso do usuário;
  - sem fonte confiável, o briefing não deve cravar dia/data textual.
- Skills de briefing atualizadas para exigir formato absoluto de data no cabeçalho quando houver fonte confiável.

## [3.6.6] - 2026-02-22

### Changed
- Briefing passa a exigir resolução de data/dia da semana no fuso do usuário (`CLAUDE.md`, default `America/Sao_Paulo`), evitando virada indevida por UTC.
- Reforço nas skills de briefing para não anunciar "hoje" com base em UTC quando o fuso local estiver em dia diferente.

## [3.6.5] - 2026-02-22

### Changed
- Correção da estratégia de checagem de atualização no briefing:
  - URLs remotas atualizadas para o caminho atual do core (`references/prumo-core.md`).
  - falha de acesso remoto (`404`, auth, rede) não pode mais ser interpretada como "sem update".
  - fallback documentado para fonte local de manutenção (`Prumo/VERSION` + `Prumo/references/prumo-core.md`) quando disponível.
- Ajuste no core de referência para refletir o novo fluxo de verificação de versão.

## [3.6.4] - 2026-02-22

### Added
- Script `scripts/generate_inbox_preview.py` para gerar `inbox-preview.html` local a partir de `Inbox4Mobile/`.
- Preview por tipo no HTML:
  - imagens (inline em base64, com fallback por caminho relativo),
  - PDFs em `iframe`,
  - textos/links inline,
  - embed de YouTube quando URL detectada.
- Botões de clipboard por item para comandos de triagem (`processar`, `mover para IDEIAS`, `descartar`).

### Changed
- Skills de briefing (`skills/briefing/SKILL.md` e `skills-briefing-SKILL.md`) agora instruem oferta opcional de preview visual para inbox multimídia.
- Core de referência (`references/prumo-core.md`) atualizado para documentar o preview visual opcional com fallback inline sem shell.

## [3.6.3] - 2026-02-22

### Changed
- Regra de processamento do inbox reforçada com commit explícito (confirmar, executar em lote e verificar).
- Skills de briefing (`skills/briefing/SKILL.md` e `skills-briefing-SKILL.md`) agora exigem:
  - confirmação de commit antes da execução;
  - deleção real do original no inbox;
  - tratamento explícito de falha por permissão (incluindo `allow_cowork_file_delete` quando aplicável);
  - relatório final de sucesso/falha por item.
- Fallback oficial para runtimes sem deleção física: marcação em `Inbox4Mobile/_processed.json` e filtro no briefing para não reapresentar itens já processados.

## [3.6.2] - 2026-02-21

### Added
- Guardrails explícitos de atualização segura para impedir sobrescrita de arquivos personalizados.
- Script `scripts/safe_core_update.sh` para atualizar apenas `PRUMO-CORE.md` com backup automático.
- Regra de validação no CI para presença do guardrail de update.

### Changed
- Instruções de update em `skills/briefing/SKILL.md`, `skills-briefing-SKILL.md` e `references/prumo-core.md` reforçam allowlist de escrita.
- Setup/reconfiguração em `SKILL.md` passa a exigir confirmação explícita para sobrescritas de arquivos sensíveis.
- Conteúdo público sanitizado para remover referências pessoais diretas em canais e exemplos.

## [3.6.1] - 2026-02-21

### Added
- Estrutura de governança de produto no GitHub (`issues`, `PR template`, `CI`, scripts de bootstrap).
- Documentação operacional para fluxo de trabalho com Codex/Cowork (`docs/WORKFLOW.md`).
- Script para bootstrap de labels (`scripts/github/bootstrap_labels.sh`).
- Script para criação de project de produto (`scripts/github/bootstrap_project.sh`).

### Changed
- Reintroduzido `VERSION` como fonte de verdade de versão pública do produto.

## [3.6.0] - 2026-02-19

### Added
- Curadoria de emails orientada à ação (`Responder`, `Ver`, `Sem ação`) com prioridade (`P1/P2/P3`).
- Janela temporal de briefing via `_state/briefing-state.json`.
- Paridade de briefing entre runtime com shell e sem shell.
