# Gotchas

Padroes de erro registrados durante o desenvolvimento. Agentes devem consultar este arquivo no inicio de cada sessao e adicionar novos padroes quando cometerem erros corrigidos pelo usuario.

---

## cowork-plugin/ foi removido

`cowork-plugin/` foi deletado em 2026-04-14. Se encontrar referencia a `cowork-plugin/skills/`, `cowork-plugin/scripts/`, ou `cowork-plugin/VERSION`, e residuo. A fonte canonica e `skills/`.

## scripts/tests/ foi descontinuado

Os smoke tests em `scripts/tests/*.sh` sairam do CI em 2026-04 (commit 39074e9) e depois sairam da distribuicao publica (commit c620653). O diretorio esta gitignored: se aparecer na maquina de dev, e residuo local. Nao ressuscitar sem decisao arquitetural nova. Cobertura viva e unit tests em `runtime/tests/` mais smoke via `prumo --version` no CI Windows.

## briefing-state.json virou last-briefing.json

Em 2026-04-22 o schema de estado de briefing foi enxugado. `briefing-state.json` com `{"last_briefing_at", "google_status", "integration_status"}` virou `last-briefing.json` com `{"at": ISO}`. Migracao silenciosa roda em `start`, `briefing` e `migrate`. Se voce precisar escrever estado persistido sobre briefing, use `update_last_briefing()` e o schema slim. A chave publica `last_briefing_at` segue no payload JSON externo por retrocompatibilidade.

## Versoes fora de sincronia

A versao do Prumo vive em 11 lugares: 7 manifestos (`plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `marketplace.json`, `.claude-plugin/marketplace.json`, `pyproject.toml`, `VERSION`) + 3 headers de skill (`skills/prumo/references/prumo-core.md`, `skills/prumo/references/modules/load-policy.md`, `skills/prumo/references/modules/dispatch.md`) + `runtime/prumo_runtime/__init__.py` (`__version__`). Se uma estiver diferente das outras, e bug. Bumpar todas juntas.

`test_version_sync.py::test_all_canonical_sources_match_runtime_version` (expandido em #83) valida automaticamente que os 10 lugares com `version` casam com `runtime.__version__`. CI quebra se alguma fonte ficar pra tras. A lista canonica esta em `VERSION_SOURCES` no proprio teste.

Nota: `.codex-plugin/marketplace.json` nao tem campo `version` (schema do Codex nao preve). Nao ressuscitar. O teste tem assert dedicado `test_codex_marketplace_does_not_carry_version_by_design` que falha se isso mudar — sinal pra atualizar `VERSION_SOURCES`.

## Google Drive snapshots (removido)

O briefing usava Google Docs como cache de email/calendario. Esse mecanismo foi removido em 2026-04-14. Se encontrar referencia a `Prumo/snapshots/email-snapshot`, `prumo_google_dual_snapshot.sh`, ou ASSERT sobre "tentar snapshots antes do MCP", e residuo. Remover.

## Diretorios e arquivos removidos (nao recriar)

`cowork-plugin/`, `bridges/`, `_lixeira/`, `commands/`, `docs/`, `ADR-*.md`, `*-ADAPTER-PLAYBOOK.md` e demais documentos de planejamento avulsos na raiz foram removidos em 2026-04-14. Nao recriar nenhum deles.

## Repo vs workspace sao pastas diferentes

O repo de dev (codigo-fonte) e o workspace do usuario (dados pessoais) sao diretorios distintos. Nunca colocar o repo dentro do workspace nem vice-versa. O `detect_nested_layout()` em `workspace_paths.py` confunde os dois se estiverem aninhados.

## Sandbox do Cowork nao tem credencial HTTPS pro GitHub

O sandbox onde o agente roda (`/sessions/ecstatic-upbeat-cerf/...`) nao tem credenciais HTTPS configuradas pro `github.com`. `git push`, `gh auth`, `gh pr create` etc. falham com "could not read Username for 'https://github.com'". Nao tentar workaround com token embutido no remote, nao pedir credencial em chat.

Fallback oficial: **Desktop Commander**. Rodar `mcp__Desktop_Commander__start_process` + `interact_with_process` para executar o comando a partir do clone real do repo na maquina do usuario (em geral `/Users/tharsovieira/Documents/DEV_Prumo`). Credenciais locais (ssh/keychain/gh) funcionam normalmente de la.

Localizar o repo real se o caminho mudar: `mdfind -name "DEV_Prumo" -onlyin "$HOME"` (macOS) ou `find ~ -maxdepth 4 -type d -name "DEV_Prumo"`.

## `tharso/prumo` nao aceita commit direto

Desde 2026-04-22 o `tharso/prumo` virou espelho publico, populado por GitHub Action a cada push em `prumo-dev/main`. Se voce:

- push direto em `tharso/prumo` -> sera sobrescrito no proximo espelhamento. Perda de trabalho garantida.
- abrir PR em `tharso/prumo` -> sera fechado como obsoleto. A instrucao no `README-MIRROR.md` manda abrir em `prumo-dev`.
- criar tag em `tharso/prumo` -> some no proximo espelhamento (force-push resetando history).

Regra: **todo desenvolvimento acontece em `tharso/prumo-dev`**. A URL publica `github.com/tharso/prumo` e contrato com o mundo (marketplace, pip, curls em docs) e nao deve mudar. O dev vive no `prumo-dev`.

Se voce nao lembra disso na hora e tentar push em `tharso/prumo`: verifica se o `origin` local aponta pra `prumo-dev.git`, nao pra `prumo.git`. Comando: `git remote -v`.

## Menus colapsados escondem sinais de primeira classe

O `start` e o `briefing` ja geram `actions[]` com varios caminhos nomeados (`align-core`, `briefing`, `continue`, `process-inbox`, `organize-day`, `repair`). Em abril/2026 os dois renderers colapsavam tudo em 4 opcoes genericas (Aceitar/Ver lista completa/Estado/Tá bom) quando `next_move` estava definido. Resultado: drift de versao nao virava opcao explicita (ficava escondido atras de "Ver lista completa") e "prumo" cru no inicio da sessao tratava briefing como unica possibilidade.

Regras:

- Renderer de menu nunca deve colapsar em "Ver lista completa" quando ha actions nomeadas. Surface ate 5 alternativas + `Ver estado tecnico` + `Ta bom por hoje`.
- Alertas de `degradation.alerts` com `action_id` (ex: `align-core`) precisam virar opcao explicita no menu, com label humano e comando inline. Label tecnico tipo "Alinhar core e wrappers canonicos" vira "Atualizar o motor (core X → runtime Y)".
- Start e briefing compartilham o helper `render_action_menu_lines(actions, next_move, workspace)` em `daily_operator.py`. Se voce vai mexer em um dos dois renderers, mexe no helper e ambos herdam.

Teste de sanidade: `message` renderizada nao pode conter "Ver lista completa" quando `actions` tem mais de 4 entradas nomeadas.

## Formato do workspace evolui, parser do runtime fica cego

Em abril/2026 o `extract_section` do runtime casava header com igualdade estrita. Funcionava enquanto o usuario escrevia `## Quente (precisa de atencao agora)` porque esse era o formato do template. Quando o usuario passou a escrever `## Quente — Quarta 22/04` (formato mais vivo, com data do dia), o runtime passou a ler **zero itens** da secao. O briefing nao quebrava: devolvia pauta vazia. Silencioso, pior que erro.

Regras:

- Parser de arquivo do usuario (PAUTA, INBOX, marcadores) nao pode depender de formato exato do template. Tolerar sufixos visuais (separador `—`, `(`, `:`, `-`, `/`, `|`) no header sem confundir secoes parecidas (ex: `Agendado` vs `Agendado Futuro`).
- Unit test com fixture sintetica **nao basta**. Todo parser de formato do usuario precisa de smoke test contra o workspace real (`DailyLife/Prumo/PAUTA.md` na maquina do Tharso) antes do merge. Se o runtime le 0 itens numa secao que tem conteudo visivel, e bug de parser, nao ausencia de dados.
- Quando o usuario reportar "o briefing esta ignorando isso" ou "nao me lembrou de X", a primeira hipotese nao e bug no briefing em si. E parser do workspace divergindo do formato que o usuario escreve hoje. Validar com smoke antes de mexer em logica de briefing.
- Header match tolerante nao e permissao pra match solto. `_section_header_matches` em `workspace.py` so aceita tail apos separadores reconhecidos. Letra nao e separador (senao `Agendado` casaria `Agendado Futuro`, bug mais sutil que o primeiro).

## zoneinfo em Windows precisa do pacote tzdata

A stdlib `zoneinfo` (PEP 615, Python 3.9+) nao traz dados de timezone embutidos em Windows. Em macOS/Linux ela le `/usr/share/zoneinfo`. Em Windows nao existe esse diretorio, entao `ZoneInfo("America/Sao_Paulo")` levanta `ZoneInfoNotFoundError`. Foi exposto em maio/2026 quando o step `Validate setup runs non-interactive on Windows` (commit 3081d88, fix #72) comecou a invocar `prumo setup` no CI Windows e quebrou imediatamente em `templates.now_display`.

Regras:

- Codigo do runtime que use `ZoneInfo` precisa do pacote `tzdata` listado em `pyproject.toml` como dependencia condicional: `'tzdata; sys_platform == "win32"'`. macOS/Linux nao instalam (le do sistema), Windows instala via pip.
- Nao adicionar tzdata como dep incondicional. So Windows precisa, e em Linux/macOS o pacote pip pode divergir do tz do sistema (causando bugs sutis de DST).
- Se um teste de integracao no CI Windows passar a invocar funcao do runtime que use timezone, garantir que `tzdata` ja esta instalado pelo install via pip antes do step.
