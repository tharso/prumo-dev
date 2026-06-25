# Runtime Paths

> **module_version: 4.22.0**
>
> Fonte canônica dos paths válidos de scripts no runtime do Prumo.

## SCRIPT_PATHS

Resolver scripts nesta ordem:

1. `scripts/` (repo do Prumo)
2. `Prumo/scripts/` (bundle instalado no workspace)

## Scripts oficiais

Observação importante:

1. alguns scripts existem como artefato gerado no workspace do usuário;
2. o repo carrega os scripts canônicos em `scripts/` (ver SCRIPT_PATHS acima).

- `prumo_cowork_doctor.sh`
- `prumo_cowork_update.sh`
- `prumo_cowork_bridge.py`

A higiene **não** entra nesta lista: é conduzida pelo agente, sem script (ver `claude-hygiene.md`). O antigo `prumo_claude_hygiene.py` não existe na arquitetura atual.


## Regra

Módulo que precisar shell deve referenciar `SCRIPT_PATHS`, não recontar a árvore de fallback como se estivesse descobrindo América toda vez.
