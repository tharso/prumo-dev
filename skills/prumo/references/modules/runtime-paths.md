# Runtime Paths

> **module_version: 4.22.0**
>
> Fonte canônica dos paths válidos de scripts no runtime do Prumo.

## Passo 0 — o runtime vem embarcado no bundle (#302)

Antes de declarar "runtime indisponível", esgotar DOIS caminhos — o PATH e o bundle:

1. **PATH:** `prumo` instalado responde direto — é o caso do macOS (Claude Code, Codex CLI), sem transporte especial.
2. **Runtime embarcado:** o bundle do plugin carrega o runtime completo em `${CLAUDE_PLUGIN_ROOT}/runtime/prumo_runtime`. Em host de filesystem partido (Cowork: container da nuvem ≠ VM do dispositivo), ele é **alcançável por transferência** — provado em 03/08: empacotar (`tar czf`), transferir pro workspace (`SendUserFile` → `device_commit_files`), extrair e executar com `PYTHONPATH=<dir> python3 -m prumo_runtime <comando>`. A VM fornece Python 3.10, a mínima do runtime desde a #301.

"Runtime inalcançável" declarado só com a sonda do PATH custou nove dias de briefings sem marcação de dia — a sonda única era a única documentada. Só depois de esgotar os dois caminhos a indisponibilidade pode ser declarada, e nomeando qual falhou.

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

O **gerador do preview do Inbox4Mobile** também não entra: ele vive dentro do pacote `prumo_runtime` e se alcança por `prumo inbox preview`, nunca por path de script. `Prumo/scripts/` no SCRIPT_PATHS acima cobre bundle de artefato gerado — não é destino de instalação, e nenhum instalador o popula. Módulo que precise do preview aponta o COMANDO, não um caminho que pode nunca existir (#289).


## Regra

Módulo que precisar shell deve referenciar `SCRIPT_PATHS`, não recontar a árvore de fallback como se estivesse descobrindo América toda vez.
