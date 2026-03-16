# Changelog

Este arquivo registra mudanças públicas do produto Prumo.

O formato segue, de forma pragmática, a ideia de Keep a Changelog e versionamento semântico.

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
