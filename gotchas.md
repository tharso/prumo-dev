# Gotchas

Padroes de erro registrados durante o desenvolvimento. Agentes devem consultar este arquivo no inicio de cada sessao e adicionar novos padroes quando cometerem erros corrigidos pelo usuario.

---

## cowork-plugin/ foi removido

`cowork-plugin/` foi deletado em 2026-04-14. Se encontrar referencia a `cowork-plugin/skills/`, `cowork-plugin/scripts/`, ou `cowork-plugin/VERSION`, e residuo. A fonte canonica e `skills/`. Smoke tests vivem em `scripts/tests/`.

## Versoes fora de sincronia

A versao do Prumo vive em 5 lugares: `plugin.json`, `.claude-plugin/plugin.json`, `pyproject.toml`, `marketplace.json` e `VERSION`. Se uma estiver diferente das outras, e bug. Bumpar todas juntas.

## Google Drive snapshots (removido)

O briefing usava Google Docs como cache de email/calendario. Esse mecanismo foi removido em 2026-04-14. Se encontrar referencia a `Prumo/snapshots/email-snapshot`, `prumo_google_dual_snapshot.sh`, ou ASSERT sobre "tentar snapshots antes do MCP", e residuo. Remover.

## Diretorios e arquivos removidos (nao recriar)

`cowork-plugin/`, `bridges/`, `_lixeira/`, `commands/`, `docs/`, `ADR-*.md`, `*-ADAPTER-PLAYBOOK.md` e demais documentos de planejamento avulsos na raiz foram removidos em 2026-04-14. Nao recriar nenhum deles.

## Repo vs workspace sao pastas diferentes

O repo de dev (codigo-fonte) e o workspace do usuario (dados pessoais) sao diretorios distintos. Nunca colocar o repo dentro do workspace nem vice-versa. O `detect_nested_layout()` em `workspace_paths.py` confunde os dois se estiverem aninhados.
