# Changelog

Este arquivo registra mudanças públicas do produto Prumo.

O formato segue, de forma pragmática, a ideia de Keep a Changelog e versionamento semântico.

## [Unreleased]

### Added
- **Comando `prumo update`** (#86) — atualiza o runtime instalado pra versão remota mais recente. Detecta método de instalação (pip vs curl install script) via marker JSON em `~/.local/share/prumo/install-method.json` (`%LOCALAPPDATA%/prumo/...` em Windows, com suporte a `XDG_DATA_HOME`). Sem marker, faz fallback explícito (testa `pip show prumo-runtime`). Modos: `--check` reporta versão remota sem executar; `--dry-run` mostra plano sem executar; `--format json` saída estruturada pra hosts/automação. Sem flags, executa update real (re-roda pip install --upgrade ou install script via bash/curl conforme método). `prumo upgrade` é alias de compatibilidade — `update` é o nome canônico (gesto cotidiano leve), `upgrade` carregava peso semântico errado (plano pago, salto de edição). 17 testes novos cobrindo detecção de método, geração de plano, alias, modos seguros e tratamento gracioso de offline. Update real **não é executado em CI** — todos os tests usam `--check`/`--dry-run` com mocks. Endpoint de versão remota: `https://raw.githubusercontent.com/tharso/prumo/main/VERSION`. Timeout 2.5s, falha graciosa se offline.

### Fixed
- **`prumo repair` agora detecta drift de versão, preservando conteúdo autoral em wrappers de raiz** (#84) — antes, o comando só checava se arquivos existiam e devolvia "nada recriável precisava de reparo" mesmo quando `PRUMO-CORE.md` declarava versão antiga (ex: workspace em `5.1.1` após `pip install --upgrade` levar runtime pra `5.3.0`). Agora `repair` lê `prumo_version` do `PRUMO-CORE.md`, compara com `runtime.__version__`, e se houver drift:
  - Move **apenas** `.prumo/system/PRUMO-CORE.md` e `Prumo/AGENT.md` (sistema + canonical do Prumo) pra `.prumo/backups/repair-version-bump/<timestamp>/` e regenera.
  - **Atualiza o bloco gerenciado** dos wrappers de raiz (`AGENT.md`, `CLAUDE.md`, `AGENTS.md`) via `merge_wrapper_content` — preserva byte-for-byte qualquer conteúdo autoral fora dos delimitadores `<!-- prumo:begin --> ... <!-- prumo:end -->`. Wrappers de raiz **nunca** entram em backup nem são regenerados do zero.
  - Reporta a transição (`5.0.0 → 5.3.0`), arquivos recriados (sistema/canonical), wrappers atualizados via merge (autorais), e path do backup.
  
  Decisão arquitetural reforçada por review do Codex: arquivos que possam conter customização do usuário **não** são tratados como artefatos descartáveis. A separação `.prumo/` (sistema, regenerável) vs raiz (autoral, preservar) é contrato — backup de wrappers seria violação. Idempotente: segunda execução em workspace em dia retorna "nada recriável precisava de reparo".

- **Convenção canônica de backups: `.prumo/backups/<scope>/<timestamp>/`** (#81 P3.8) — antes existia drift entre dois paths: `backup_root_for()` em `workspace.py` e `backup_path_for()` (runtime-migrate) já usavam `.prumo/backups/` plural com scope, mas `bump_system_canonicals_for_repair` (#84) escrevia em `.prumo/backup/repair-version-bump-<ts>/` (singular) e `migrate_skills` (#79) escrevia em `.prumo/system/backup/relocate-skills-<ts>/` (singular aninhado em `system/`). Convergido: ambos escritores agora usam `.prumo/backups/<scope>/<timestamp>/` com convenção uniforme. Backups em `.prumo/backup/` (singular) de runtimes antigos permanecem **intocados** — sanitize varre os dois paths quando rodada e consolida sobreviventes em `.prumo/backups/legacy/`. Skills (`prumo`, `prumo-core.md`, `file-protection-rules.md`, `version-update.md`, `claude-hygiene.md`, módulo `sanitization.md`) atualizadas pra documentar o caminho canônico, com nota explicando o legado.

### Tests
- 8 testes novos em `test_repair.py` cobrindo: detecção de drift (em dia, defasado, sem PRUMO-CORE.md), repair sem drift (não toca canonicals, não cria backup, sem merge), repair com drift (regenera só sistema/canonical, faz merge nos wrappers de raiz, backup contém só sistema/canonical), idempotência, e **preservação de conteúdo autoral** em CLAUDE.md fora do bloco gerenciado durante drift.
- 1 teste novo `test_repair_writes_backup_under_canonical_backups_path` afirma escrita no path canônico e preservação de legado em `.prumo/backup/`. Suite total: 126 testes verdes.

## [5.3.0] - 2026-05-05

### Fixed
- **`prumo setup` em Windows não falha mais com `ZoneInfoNotFoundError`** — `pyproject.toml` ganhou dependência condicional `tzdata; sys_platform == "win32"`. A stdlib `zoneinfo` não traz dados de timezone embutidos em Windows (em macOS/Linux ela lê do sistema), o que quebrava `ZoneInfo("America/Sao_Paulo")` no step `Validate setup runs non-interactive on Windows` introduzido em [commit 3081d88]. Tornou o gap antigo visível.
- **Despacho do Cowork em invocação curta** (#64) — quando o usuário diz "prumo" cru, o host carregava `prumo:setup` por falta de skill dedicada à invocação curta, e acabava improvisando lendo `CLAUDE.md`. Agora o plugin tem skill nova `prumo:abrir` que dispara em "prumo", "ei prumo", "olá prumo" e segue o protocolo de dispatch (identidade mínima + scan leve + saudação proativa). Templates do `AGENT.md` e wrappers (`CLAUDE.md`, `AGENTS.md`) atualizados pra apontar a skill como instrução primária — o atalho `prumo` no shell vira atalho equivalente, não única via. Descriptions de `briefing` e `setup` aparadas: `briefing` não dispara mais em "bom dia" cru (alinhamento com decisão #69), `setup` requer intenção explícita de configuração e não dispara em "prumo" cru.
- **Comandos shell anunciados aos hosts agora batem com o parser** (#64 follow-up, audit Codex em #81 P1.2) — `--refresh-snapshot` foi removido de todos os lugares (4 templates/payloads + assinatura de `build_briefing_payload`). A flag foi removida do parser em algum momento mas continuou sendo anunciada, e o parâmetro `refresh_snapshot` em `build_briefing_payload` era dead code (recebido e nunca usado). Skill `prumo:abrir` corrigida pra usar `prumo` puro (root command não aceita `--workspace`). Placas antigas em 4 lugares (`render_wrapper_merge_block` em `workspace.py`, fallback chain em `agent-md-template.md`, texto interno de `briefing/SKILL.md` e `start/SKILL.md`) atualizadas pra apontar `prumo:abrir` como rota primária.
- **Skill `higiene` referenciava módulo inexistente** (`perfil-hygiene.md`) — corrigido para `claude-hygiene.md`, que é o módulo real (cita audit Codex em #81 P2.5).
- **Drift de versão em manifestos distribuídos e headers de skills canônicas** (#83, audit Codex em #81 P1.3) — 6 arquivos estavam declarando `5.1.1` enquanto runtime, `pyproject.toml`, `VERSION` e `plugin.json` raiz já estavam em `5.2.0`. Bumpados: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `skills/prumo/references/prumo-core.md` (header `prumo_version`), `skills/prumo/references/modules/dispatch.md` e `skills/prumo/references/modules/load-policy.md` (headers `module_version`). `test_version_sync.py` expandido para cobrir todos os 10 lugares com `version`/`__version__` (mais teste dedicado documentando a exceção do `.codex-plugin/marketplace.json`, que não tem campo por design do schema do Codex). CI agora quebra automaticamente se algum manifesto sair de sincronia.
- **Wheel publicado agora carrega skills, plugin.json e VERSION** (#82, audit Codex em #81 P1.1) — antes, o wheel empacotava só `runtime/prumo_runtime/`, e instalações via `pip install` ou `curl | bash` produziam runtime órfão. `prumo setup` levantava `TypeError` porque `install_skills()` fazia `repo / "skills"` quando `repo_root_from()` retornava `None`. Fix em três frentes: (1) `pyproject.toml` ganhou `[tool.hatch.build.targets.wheel.force-include]` mapeando `skills/`, `plugin.json` e `VERSION` para `prumo_runtime/_bundled/` dentro do package; (2) `repo_root_from()` ganhou fallback que aponta para `_bundled/` quando subir a árvore não encontra repo real (caso típico de wheel em `site-packages/`); (3) `install_skills()` trata `repo is None` graciosamente com retorno vazio em vez de crashar. Todos os call sites de `repo_root_from()` (em `templates.py`, `briefing.py`, `start.py`, `inbox_preview.py`) automaticamente passam a funcionar em wheel install sem mudanças individuais. Adicionado job CI `wheel-install-smoke` que constrói wheel, instala em venv limpo, roda `prumo setup` e verifica que `.prumo/skills/abrir/SKILL.md` + `.prumo/system/PRUMO-CORE.md` (com `prumo_version: 5.2.0`) materializam corretamente — defesa permanente contra essa categoria de bug. Validado manualmente em venv Python 3.11 antes do commit.
- **sdist tarball agora contém os assets necessários pra reconstruir o wheel** (#82 follow-up apontado por Codex) — o `force-include` do wheel é resolvido em build time a partir do CWD, mas como `[tool.hatch.build.targets.sdist].include` não listava `skills/` nem `plugin.json`, o sdist saía sem esses arquivos e tentar reconstruir wheel a partir do sdist extraído falhava com `FileNotFoundError: Forced include not found`. Adicionado `/skills` e `/plugin.json` ao include do sdist. Job `wheel-install-smoke` ganhou steps que (a) validam `prumo start --format json` e `prumo briefing --format json` retornando `canonical_refs` apontando pro `_bundled/` (subindo o sarrafo de "produto não crash" para "produto não empobrecido"), e (b) fazem roundtrip sdist → wheel verificando que o wheel reconstruído contém o bundle.

### Added
- **Skill `prumo:abrir`** ([commit d213cfe]) — porta de entrada para invocação curta. Curta de propósito: redirect pro módulo `dispatch.md` que já existia. Resolve #64 sem mexer no namespace de core (alternativa B, renomear `skills/prumo/` pra `skills/setup/`, foi descartada por arrastar `references/`, `references/modules/` junto, ficando incoerente — `briefing` lendo módulo canônico de dentro de pasta chamada `setup`).
- **Teste `test_announced_commands.py`** — valida que todos os comandos shell anunciados aos hosts (via templates, payloads, skills) existem de fato no parser do CLI. Defesa contra a categoria de bug pego pelo Codex em #81 P1.2 (templates/payloads anunciando flags ou comandos que o parser não aceita).

- **Comando `prumo migrate-skills`** ([commit daf9c6c]) — migra workspaces pré-5.2.0 (skills em `Prumo/skills/` ou `Prumo/skills_OLD/`) para a estrutura nova (`.prumo/skills/`). Pre-flight obrigatório consulta `DECISIONS.md` por tópicos relevantes (`skills-distribution`, `workspace-layout`) e mostra plano antes de executar. Backup automático em `.prumo/backup/relocate-skills-<timestamp>/`. Re-renderiza `Prumo/AGENT.md` e `.prumo/system/PRUMO-CORE.md` via `repair_workspace`. Loga em `.prumo/logs/architectural-ops.log` (formato `<ISO>\t<op>\t<message>`). Idempotente: workspaces já migrados, sem skills, ou em estado ambíguo saem limpos. Flag `--yes` pula confirmação para automação. Resolve a Fase 3 plena da #77 e plumba a Melhoria 6 da #78 num caso de uso real.

### Tests
- 17 testes novos em `test_migrate_skills.py` cobrindo todos os 5 estados do detector, idempotência, workspace inválido, pre-flight em modo TTY e não-TTY, execução com `--yes`, formato do log e busca em `DECISIONS.md`.
- `test_announced_commands.py` (3 testes) — valida que todo comando shell anunciado em template/payload existe no parser. Defesa permanente contra a categoria do bug do Codex (#81 P1.2).
- `test_version_sync.py` ampliado — `VERSION_SOURCES` cobre 10 lugares (manifestos `.claude-plugin/`, `.codex-plugin/`, headers de `prumo-core.md`/`dispatch.md`/`load-policy.md`, plus `pyproject`/`VERSION`/`__init__.py`/`plugin.json`/`marketplace.json`). Mais teste dedicado documentando que `.codex-plugin/marketplace.json` não tem campo `version` por design do schema do Codex.
- Job CI novo `wheel-install-smoke`: build wheel via `python -m build`, instala em venv limpo, roda `prumo setup`, verifica que as 8 skills + `PRUMO-CORE.md` materializam, valida `prumo start --format json` e `prumo briefing --format json` apontam `canonical_refs` pro `_bundled/`, e roda roundtrip sdist → wheel pra garantir que o tarball reconstrói o wheel completo.
- Suite total: 117 testes verdes (eram 96 na 5.2.0; +17 do migrate-skills, +3 dos comandos anunciados, +1 do codex-marketplace exception).

### Docs
- README ganha seção "Migração entre layouts" mapeando as três eras (pré-#65, #65, #77) e os comandos correspondentes (`prumo migrate` e `prumo migrate-skills`).
- README atualiza versão para `5.2.0` (estava `5.1.1` por débito do release anterior).
- `gotchas.md` atualiza a entry "Versoes fora de sincronia" — para de descrever auditoria como manual e aponta `test_version_sync.py` como validador automático em CI.
- `gotchas.md` ganha entry sobre `zoneinfo` em Windows precisar do pacote `tzdata` (com regra de não adicionar incondicional).

### Governance
- Protocolo de revisão Codex consolidado nesta release: cada ajuste a uma issue de bug ou packaging foi seguido de comentário detalhado na issue + pedido explícito de review do @codex. O protocolo pegou três bugs reais nesta janela: comandos shell inválidos sendo anunciados (#82 P1.2 follow-up), placas antigas competindo com `prumo:abrir` em arquivos não tocados pelo commit inicial (#82 P2.4), e sdist tarball saindo sem skills (#82 follow-up posterior à aprovação inicial). Vale a pena.

## [5.2.0] - 2026-05-04

### Changed
- **Skills moram em `.prumo/skills/`** (pasta de infraestrutura invisível), não mais em `Prumo/skills/` (visível). Substitui parcialmente a decisão de 2026-04-15 (#65) — preserva a cadeia de fallback (slash → CLI → skill direto) que motivou a #65, mas alinha o destino ao princípio workspace-first registrado em 2026-04-22 (#73): infra invisível em `.prumo/`, dados visíveis em `Prumo/`. Resolve drift detectado na validação operacional da #73, em que `Prumo/skills/` fora renomeada pra `Prumo/skills_OLD/` sem destino articulado.
- **Workspaces existentes precisam migração manual nesta versão**. O comando `prumo migrate skills-to-system` (com pre-flight obrigatório) será adicionado em release subsequente. Migração manual hoje: mover `Prumo/skills_OLD/` (ou `Prumo/skills/`, dependendo do estado do workspace) para `.prumo/skills/`, deletar `Prumo/AGENT.md` e `.prumo/system/PRUMO-CORE.md`, e rodar `prumo repair --workspace <path>` para regenerar com os caminhos novos.

### Governance
- **`DECISIONS.md` ganha índice temático no topo + vocabulário controlado de tópicos**. Cada nova entrada inclui campo "Relações com decisões anteriores" (revoga, estende, mantém, ou "nenhuma identificada após consulta ao índice"). Entradas anteriores não são reescritas. Plumagem da Melhoria 1, 2 e 3 da #78 ([commit cb5ef3f]).
- **Workflow `needs-review-detector` em `.github/workflows/`** marca toda segunda às 9h UTC issues que parecem concluídas com label `status/needs-review` para revisão humana antes de fechar. Heurística com negation patterns; não fecha automaticamente. Plumagem da Melhoria 5 da #78 ([commit 965de71]).
- **CLAUDE.md ganha checklist operacional explícito de 6 passos** antes de qualquer operação arquitetural, e bloco específico sobre operações manuais (`mv`/`rm`) com efeito arquitetural exigindo commit de registro. Aplicado retroativamente: a renomeação `Prumo/skills/` → `Prumo/skills_OLD/` em 22/04 (#73) é citada como exemplo do padrão de fantasma git que esta regra previne ([commit cb5ef3f]).

### Fixed
- **`prumo setup` roda em CI e stdin redirecionado sem `EOFError`** (#72). `prompt_choice` e `ask_if_missing` detectam stdin não-TTY (ou env var `PRUMO_NONINTERACTIVE`); prompt com default usa default + log explícito; sem default, falha com mensagem clara. Windows CI ganha step `Validate setup runs non-interactive on Windows` que valida o caminho de automação ([commit 3081d88]).
- **Truncate do `hottest` no panorama do briefing**: `list_or_placeholder` agora aplica `shorten_pauta_item` em cada item (extrai `[tag] **título** | cobrar: DD/MM`), não despeja a descrição inteira. Suffix `(+N)` quando há overflow. Antes, panorama virava muro de texto de 1500+ chars ([commit 8237392]).

### Tests
- 96 testes verdes (eram 90 na 5.1.1; +6 em `NonInteractiveStdinTests`).

### Docs
- README e CHANGELOG não citam mais `Prumo/skills/` em paths (referências históricas a `Prumo/skills_OLD/` foram preservadas como contexto na decisão arquitetural).
- Convenção de assinatura: commits redigidos por agente incluem trailer `Co-authored-by: Claude (Cowork) <noreply@anthropic.com>`. Tharso continua como autor primário (aprova e dirige), agente vira co-autor.

## [5.1.1] - 2026-04-22

### Fixed
- **Menu de alternativas no briefing e no start para de colapsar em "Ver lista completa"**: quando `next_move` estava definido, o renderer enterrava todas as opções nomeadas (briefing, continue, process-inbox, organize-day, align-core) atrás de 4 genéricas (Aceitar/Lista/Estado/Tá bom). Agora os dois renderers surfam até 5 alternativas nomeadas + "Ver estado técnico" + "Tá bom por hoje". Abrir sessão com "prumo" cru mostra de cara os caminhos disponíveis em vez de tratar briefing como única possibilidade.
- **Drift de versão entre workspace e runtime vira opção explícita no menu**: quando `core_outdated` é detectado, a opção `align-core` aparece como item nomeado com label humano contextual ("Atualizar o motor (core X → runtime Y)") e o comando `prumo migrate` inline. Antes, o drift aparecia só no preflight e a opção de atualizar ficava enterrada em "Ver lista completa".

### Changed
- `daily_operator.py`: novo helper `render_action_menu_lines(actions, next_move, workspace)` compartilhado entre `start` e `briefing`. Prioridade explícita: align-core, briefing, continue, process-inbox, organize-day, repair, kickoff. Source of truth única para renderização de menu.
- `suggest_core_alignment_action` passa a gerar label dinâmico usando as versões reais do workspace em vez do texto técnico genérico "Alinhar core e wrappers canônicos".

### Tests
- 4 novos testes cobrindo os dois bugs (2 em `test_start.py`, 2 em `test_briefing.py`). Total: 45 testes verdes.

### Docs
- Gotchas.md ganha entrada "Menus colapsados escondem sinais de primeira classe" para prevenir regressão.

## [5.1.0] - 2026-04-22

### Added
- **Codex CLI como target de primeira classe**: novo `.codex-plugin/plugin.json` + `.codex-plugin/marketplace.json` com schema próprio do Codex (source url, policy, category). Instalação agora funciona via `codex plugin marketplace add https://github.com/tharso/prumo.git`.
- **Antigravity (Gemini) como target de primeira classe**: novo `scripts/prumo_antigravity_install.sh` que copia `skills/` pra `~/.gemini/antigravity/skills/` (escopo global, default) ou `<pwd>/.agent/skills/` (escopo workspace, via `--scope workspace`). Funciona com checkout local ou snapshot baixado via curl. Usa rsync quando disponível, cai em `cp -R` quando não.
- **Receita de instalação documentada pros quatro canais**: README reorganizado em seções Runtime, Cowork/Claude Code, Codex CLI, Antigravity. Zero ambiguidade sobre qual comando rodar em cada host.

### Changed
- Mirror workflow (`.github/workflows/mirror-to-prumo.yml`) agora inclui `.codex-plugin/` e `scripts/prumo_antigravity_install.sh` no subset distribuído pra `tharso/prumo`.
- Estrutura no README atualizada pra refletir `.claude-plugin/`, `.codex-plugin/` e `scripts/` como cidadãos de primeira classe. `docs/` removido do diagrama (foi removido do repo em 2026-04-14).

### Docs
- Decisão arquitetural "Distribuicao multi-cliente" registrada em `DECISIONS.md` como contrato: adicionar novo host exige manifesto próprio, script de instalação, inclusão no mirror e linha no CHANGELOG. Nenhum host pode receber feature que dependa de capacidade exclusiva dele.

## [5.0.0] - 2026-04-22

### Infrastructure (breaking for direct cloners, transparente pro usuário do plugin)
- **Split dev/dist**: o desenvolvimento do Prumo mudou de casa pra `tharso/prumo-dev` (repo aberto com issues, history, reviews). `tharso/prumo` virou espelho público limpo, populado automaticamente a cada push em `prumo-dev/main` por workflow de CI. Quem instala via marketplace (Cowork, Claude Code), `pip install prumo-runtime` ou clone direto não muda nada — a URL pública continua `tharso/prumo`. O espelho só carrega o subset distribuível (`skills/`, `runtime/prumo_runtime/`, `.claude-plugin/`, README, LICENSE, CHANGELOG, VERSION, pyproject, scripts de runtime). Arquivos internos de dev (`DECISIONS.md`, `CLAUDE.md`, `AGENT.md`, `.github/`, `dev-archive/`, gotchas, etc.) ficam em `prumo-dev` e não vazam pro usuário final.
- **Major bump**: quebra de contrato apenas para quem clonou direto de `tharso/prumo.git` antes do split, porque a history foi reescrita (force-push do mirror). Instalação via plugin manager e `pip` são transparentes.
- **Não commitar em `tharso/prumo` direto**: qualquer PR, commit ou tag nesse repo é sobrescrito no próximo espelhamento. Desenvolvimento acontece em `prumo-dev`, pronto.

### Scope
- MVP limpo de fumaça: multi-conta e Apple Reminders saem do horizonte ativo do produto. Continuam como história e código legado onde já existirem, mas deixam de aparecer no contrato principal, nos playbooks e na conversa do dia.
- Gmail, Google Calendar e Google Drive passam a entrar no MVP preferencialmente via conectores oficiais/MCP do host. A integração Google direta no runtime fica rebaixada para fallback/infra futura.

### Changed
- O `start --format json` ficou mais seco para adapters: `state_flags` agora carrega só o que move decisão do MVP, sem puxar Apple Reminders de volta para a mesa.
- Os templates do workspace ficaram mais explícitos sobre a ordem correta de consumo do JSON: primeiro `degradation`, `next_move`, `selection_contract` e `state_flags`; a prosa vem depois.
- `prumo setup` parou de agir como despejador de arquivos. Agora ele roda em etapas curtas, pode pedir o caminho do workspace quando ele não vier por flag e cria workspaces novos no layout alvo: wrappers leves na raiz, memória viva em `Prumo/` e infraestrutura local em `/.prumo/`.
- `prumo migrate` deixou de ser maquiagem de workspace legado. Agora ele faz o transplante flat→nested, move memória viva para `Prumo/`, estado técnico para `/.prumo/`, recria wrappers mínimos na raiz e guarda backup antes de trocar as placas de lugar.
- `prumo` em workspace recém-nascido deixou de sugerir briefing de apartamento vazio. Quando ainda não existe tração real, a primeira ação passa a ser uma sessão de arranque guiada em vez de panorama ornamental do nada.
- O `kickoff` deixou de ser bilhete vago para host improvisar. `start --format json` agora expõe `kickoff_contract`, `initial_question` e regras para a primeira devolução organizada. O contrato passou a ser dump-first: primeiro o usuário despeja o caos, depois o Prumo organiza em poucos blocos e só então afunila.
- A entrada do kickoff ficou mais limpa: `prumo` em workspace recém-nascido já entra no convite de despejo inicial, sem gate artificial de `aceitar` antes da conversa começar.

### Docs
- Os playbooks de `Codex`, `Claude Code`, `Antigravity` e `Gemini CLI` agora registram, sem charada, como consumir `start/briefing` estruturados sem voltar ao vício de pescar string.
- Wrappers e playbooks agora também proíbem um vício mais específico e igualmente chato: narrar bastidor na invocação curta (`vou acionar o runtime`, `vou ler o JSON`, `vou abrir arquivo`). O host executa primeiro e fala depois.
- O canon agora ganhou um contrato explícito para contexto externo via host em [canon/contracts/host-external-context.md](/Users/tharsovieira/Documents/DailyLife/Prumo/canon/contracts/host-external-context.md). Em português menos solene: Gmail, Calendar e Drive entram preferencialmente pelo conector oficial do host, e o Prumo continua dono do sentido do dia.
- O canon agora também ganhou [canon/contracts/host-context-normalization.md](/Users/tharsovieira/Documents/DailyLife/Prumo/canon/contracts/host-context-normalization.md), para impedir que cada host despeje seu próprio dialeto cru no briefing e chame isso de integração.
- O canon agora ganhou [canon/orchestration/kickoff.md](/Users/tharsovieira/Documents/DailyLife/Prumo/canon/orchestration/kickoff.md), separando briefing de sessão de arranque e impedindo que workspace virgem receba panorama ornamental como presente de boas-vindas.
- Novo [WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/WORKSPACE-LAYOUT-AND-ADOPTION-PLAN.md), fixando a proxima cirurgia do produto: raiz minima, memoria viva em `/Prumo/`, sistema em `/.prumo/`, overlay em `/Prumo/Custom/` e `setup` menos porteiro perdido.
- Novo [HOST-CONSUMPTION-VALIDATION.md](/Users/tharsovieira/Documents/DailyLife/Prumo/HOST-CONSUMPTION-VALIDATION.md), transformando “validação real de host” em protocolo curto em vez de mito oral de corredor.
- O protocolo de consumo por host agora cobre também o pré-cenário de `migrate` para workspaces legados, porque ignorar a primeira pedra real do caminho seria um bom jeito de chamar teatro de validação de campo.
- Relatórios de validação do `Claude Code` e do `Antigravity` ficaram registrados em [validation/host-consumption/claude-code-2026-03-28.md](/Users/tharsovieira/Documents/DailyLife/Prumo/validation/host-consumption/claude-code-2026-03-28.md) e [validation/host-consumption/antigravity-2026-03-28.md](/Users/tharsovieira/Documents/DailyLife/Prumo/validation/host-consumption/antigravity-2026-03-28.md).
- O README e a bridge de Apps Script foram alinhados a uma decisão menos histérica: multi-conta fica documentado como ponte futura, mas sai do MVP. Uma conta Google bem integrada basta para a primeira entrega.

## [4.19.0] - 2026-04-20

### Removed
- **HANDOVER sai do produto do usuário (issue #68).** `HANDOVER.md`, `HANDOVER.summary.md` e o comando `/prumo:handover` deixam de fazer parte do contrato do usuário final. A prática era ferramenta de desenvolvimento do Prumo vazando pro produto. A coordenação entre múltiplos agentes agora acontece exclusivamente via `.prumo/state/agent-lock.json` (lock curto, sem narrativa).
- Referências a handover removidas de `prumo-core.md`, `briefing-procedure.md`, `load-policy.md`, `multiagent.md`, `interaction-format.md`, `file-protection-rules.md`, `changelog-setup.md`, `file-templates.md` e `skills/prumo/SKILL.md`.

### Changed
- **Sanitize refocalizada**: escopo passou a ser exclusivamente `.prumo/` (sistema). Cuida de backups velhos, cache expirado e arquivos de estado que crescem demais. Não toca em arquivos do usuário.
- **Faxina sem duplicação**: a limpeza de estado técnico saiu da faxina. Agora a triade é clara: `sanitize` cuida do sistema (`.prumo/`, automático, cooldown), `faxina` cuida de arquivos do usuário (`Prumo/`, automático no briefing), `higiene` cuida de manutenção assistida do workspace do usuário (pergunta antes de mexer).
- Multiagente (`multiagent.md`) reescrito como lock-only. Sem handover narrativo, sem validação cruzada PENDING/REJECTED.

## [4.16.6] - 2026-03-27

### Fixed
- O instalador do runtime para macOS/Linux deixou de depender de um checkout local implícito. Quando for executado via `curl`/process substitution, ele agora baixa um snapshot do repositório e instala a partir dali, em vez de tropeçar em `/dev` como se isso fosse o projeto.
- O README agora também explicita o caminho certo para quem quer instalação editável de desenvolvimento a partir de um clone local.
- `runtime/tests/test_start.py` deixou de apodrecer no calendário. Os cenários que dependiam de "briefing hoje" e "briefing ontem" agora calculam datas relativas ao fuso local em vez de ficar presos a março de 2026 como mosquito no âmbar.

## [4.16.5] - 2026-03-25

### Changed
- O loop diário ficou mais magro: `workflow-scaffold` saiu das ações padrão de `start` e `briefing`. A estrutura continua existindo, mas parou de pedir palco antes de ter peça.
- O `start` e o `briefing` em texto ficaram menos painel de controle e mais operador: quando há `next_move` claro, a saída humana para de despejar cardápio completo e passa a conduzir pelo movimento recomendado.
- `Apple Reminders`, quando está fora de foco ou desconectado, deixou de roubar bloco próprio no briefing padrão. Continua no estado técnico, mas saiu da sala principal.

### Fixed
- O produto parou de empurrar complexidade prematura para a primeira tela do dia. Menos vitrine, mais condução.

## [4.16.4] - 2026-03-25

### Added
- `start` e `briefing` agora expõem `selection_contract`, deixando explícito que `1`, `a`, `aceitar`, `seguir` e equivalentes curtos devem executar `next_move` direto, sem rerodar `start` nem devolver menu por insegurança.
- Quando o core do workspace estiver defasado, o runtime passa a oferecer ação concreta de alinhamento (`align-core`) em vez de fingir que drift é nota de rodapé decorativa.

### Changed
- `adapter_hints` e `daily_operation` agora carregam regras mais duras de interação para host: confirmação curta executa a ação recomendada e, depois da execução, o correto é relatar resultado e mudanças na documentação viva antes de abrir novas opções.

### Fixed
- O contrato ficou menos aberto à interpretação criativa do host. Traduzindo: menos maître indeciso, mais operador.

## [4.16.3] - 2026-03-25

### Changed
- `start` e `briefing` passaram a expor `next_move` explicitamente. O runtime parou de sugerir uma coisa e entregar outra escondida na fila de ações.
- A ordenação de `actions[]` agora acompanha melhor o estado do dia: se já houve briefing e existe frente quente, a continuação sobe; se a fila está encostada, a triagem sobe; se o dia ainda não abriu, briefing continua primeiro.
- `daily_operation` agora declara regras de conversa e de documentação viva, porque host sem cerca tende a confundir ajuda com reforma.

### Fixed
- O Prumo ficou menos “menu de restaurante” e mais operador diário: menos opções genéricas, mais condução para a próxima jogada plausível.

## [4.16.2] - 2026-03-23

### Added
- Novo comando canônico `prumo inbox preview`, porque o preview do Inbox4Mobile já era parte real do produto e estava morando como capacidade implícita em vez de comando com endereço próprio.
- Nova camada compartilhada `inbox_preview.py`, reaproveitando a lógica de geração e leitura do preview sem deixar o `briefing` bancar dono exclusivo dessa peça.

### Changed
- `prumo start --format json` agora anuncia `inbox_preview_entrypoint` em `adapter_hints`. O host não precisa mais inventar nome de comando como quem escreve fanfic de CLI.
- O gerador de preview foi trazido para dentro do pacote do runtime, para a vitrine do inbox parar de depender do script escondido no plugin do Cowork.

### Fixed
- O gap entre “preview existe no Prumo” e “preview existe no runtime” foi finalmente fechado. Antes era um recurso verdadeiro com endereço falso. Agora os dois moram na mesma cidade.

## [4.16.1] - 2026-03-22

### Added
- Nova ação `process-inbox` no operador diário, para o runtime parar de agir como se fila encostada fosse detalhe cosmético.
- Novo workflow de CI em [ci.yml](/Users/tharsovieira/Documents/DailyLife/Prumo/.github/workflows/ci.yml), com suíte e smoke em `ubuntu-latest` e `macos-latest`, além de smoke real de install/update e comandos do runtime em `windows-latest`.

### Changed
- As ações estruturadas do runtime agora carregam `documentation_targets` e `outcome`, o que dá ao host instrução melhor sobre o que atualizar e o que deve sair de cada passo.
- `start` ganhou mais faro operacional: quando a fila está encostada, a sugestão deixa de bancar a paisagem e passa a mandar processar inbox.

### Fixed
- O core canônico do plugin e seus módulos voltaram a sincronizar com a versão do runtime. Release com placa torta é coisa de oficina desatenta.

## [4.16.0] - 2026-03-22

### Added
- Novo núcleo explícito de plataforma em `platform_support.py` e `capabilities.py`, para o runtime parar de agir como se “macOS por osmose” fosse arquitetura.
- Nova camada `daily_operator.py`, que formaliza o Prumo como operador diário: briefing, continuação, documentação viva e scaffolding de workflows.
- Novo arquivo autoral `Referencias/WORKFLOWS.md` criado pelo runtime, porque a próxima fase precisa de fundação para workflows sem fingir que eles já nasceram prontos.
- Novos scripts PowerShell `scripts/prumo_runtime_install.ps1` e `scripts/prumo_runtime_update.ps1`, abrindo a porta mínima funcional para Windows sem depender de rezas e screenshots.

### Changed
- `workspace_overview`, `context-dump`, `prumo start --format json` e `prumo briefing --format json` agora expõem `platform`, `capabilities` e `daily_operation`. O runtime finalmente passou a falar como produto, não só como checklist de integração.
- A saída de `start` e `briefing` agora carrega ações mais adultas: continuidade de trabalho, organização do dia, documentação viva e registro de candidatos a workflow.
- A integração Google deixou de depender implicitamente do Keychain do macOS. Fora do macOS, o runtime passa a usar storage local próprio, fora do workspace.
- `Apple Reminders` saiu do centro da fase atual. Continua existindo como provider e estado do runtime, mas agora aparece como backlog/degradação tolerável, não como bengala conceitual do produto.

### Docs
- `README.md` foi alinhado à fase nova: `Antigravity` como trilho principal do piloto, `Codex` como referência técnica, `Cowork` em backlog preparado e Windows oficialmente dentro do escopo.

## [4.15.5] - 2026-03-22

### Changed
- Os wrappers do workspace ficaram mais chatos com dois vícios que apareceram no campo: rodar comando extra sem necessidade e insistir na mesma linha depois de um erro explícito. Produto bom não precisa de tutor de obviedade, mas alguns hosts claramente ainda precisam.
- `prumo briefing` agora aceita `--format json`, porque alguns hosts claramente precisavam de uma porta estruturada oficial em vez de continuar batendo a cabeça na mesma flag inválida.

### Docs
- O playbook de `Antigravity` agora registra o reteste já com briefing estruturado oficial: a rota curta passou limpa, e o problema remanescente ficou mais honestamente concentrado em permissão por app.
- O playbook de `Antigravity` agora registra o resultado real do teste de campo: bem melhor do que o `Gemini CLI`, ainda longe de comportamento impecável.
- O plano de adapters agora fecha uma fotografia curta dos hosts já testados, o que evita transformar memória recente em lenda oral de corredor.
- Novo [COWORK-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/COWORK-ADAPTER-PLAYBOOK.md), separando sem açúcar duas coisas que estavam se misturando: `Cowork` como casca fina de shell e `Cowork` como invocação curta/nativa.
- O contrato de invocação e as notas de execução agora registram explicitamente que o `Cowork` ainda falha na rota curta e não deve ganhar licença para improvisar runtime via plugin/skill quando isso acontecer.
- `README.md`, wrappers e contrato de invocação agora também apontam a rota estruturada de briefing, para o host parar de achar que precisa inventar JSON em cima de prosa.

## [4.15.4] - 2026-03-21

### Changed
- `prumo start --format json` agora expõe `adapter_contract_version`, `workspace_resolution` e `adapter_hints`, para o adapter parar de jogar tarô em cima do runtime.
- Os wrappers gerados do workspace (`AGENT.md`, `CLAUDE.md`, `AGENTS.md`) agora dizem explicitamente que host bom lê esses metadados antes de inventar moda.

### Docs
- O contrato de invocação e o plano de adapters foram alinhados a esse JSON mais explícito, porque chamar isso de "detalhe de implementação" seria um ótimo jeito de quebrar cinco hosts ao mesmo tempo.
- Novo [CODEX-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CODEX-ADAPTER-PLAYBOOK.md) fixando, sem misticismo, o que significa dizer que o Codex é o primeiro adapter implementado.
- Novo [CLAUDE-CODE-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CLAUDE-CODE-ADAPTER-PLAYBOOK.md), para o projeto parar de tratar `Claude Code` como "Cowork sem vitrine".
- Novo [GEMINI-CLI-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/GEMINI-CLI-ADAPTER-PLAYBOOK.md), preparando o próximo host limpo para validação de campo.
- Novo [ANTIGRAVITY-ADAPTER-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/ANTIGRAVITY-ADAPTER-PLAYBOOK.md), porque o fracasso do `Gemini CLI` não autoriza nem condenação automática nem ingenuidade automática no próximo host da família.

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
- Briefing passa a priorizar snapshots privados `Prumo/snapshots/email-snapshot` em Google Docs como fonte multi-conta para agenda e emails.
- Guia operacional movido para [bridges/google-apps-script/apps-script-setup.md](/Users/tharsovieira/Documents/DailyLife/Prumo/bridges/google-apps-script/apps-script-setup.md), em vez de seguir apodrecendo em `docs/` ignorado.

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
