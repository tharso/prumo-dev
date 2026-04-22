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

A versao do Prumo vive em 10 lugares: 7 manifestos (`plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `marketplace.json`, `.claude-plugin/marketplace.json`, `pyproject.toml`, `VERSION`) + 3 headers de skill (`skills/prumo/references/prumo-core.md`, `skills/prumo/references/modules/load-policy.md`, `skills/prumo/references/modules/dispatch.md`). Se uma estiver diferente das outras, e bug. Bumpar todas juntas. Comando rapido pra auditar: `grep -rn "X\.Y\.Z" --include='*.json' --include='*.toml' --include='VERSION' --include='*.md'`.

Nota: `.codex-plugin/marketplace.json` nao tem campo `version` (schema do Codex nao preve). Nao ressuscitar.

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
