# Runtime Paths

> **module_version: 4.13.1**
>
> Fonte canônica dos paths válidos de scripts no runtime do Prumo.

## SCRIPT_PATHS

Resolver scripts nesta ordem:

1. `scripts/`
2. `Prumo/cowork-plugin/scripts/`
3. `Prumo/scripts/`

## Scripts oficiais

Observação importante:

1. alguns scripts existem como artefato gerado no workspace do usuário (ex.: `scripts/prumo_google_dual_snapshot.sh`);
2. o repo também pode carregar um template/fallback canônico do mesmo script em `cowork-plugin/skills/prumo/references/`.

- `prumo_auto_sanitize.py`
- `prumo_archive_cold_files.py`
- `prumo_claude_hygiene.py`
- `prumo_cowork_doctor.sh`
- `prumo_cowork_update.sh`
- `prumo_cowork_bridge.py`
- `prumo_sanitize_state.py`
- `prumo_briefing_state.py`
- `safe_core_update.sh`
- `generate_inbox_preview.py`
- `prumo_google_dual_snapshot.sh`

## Regra

Módulo que precisar shell deve referenciar `SCRIPT_PATHS`, não recontar a árvore de fallback como se estivesse descobrindo América toda vez.
