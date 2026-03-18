---
name: sanitize
description: >
  Compacta estado operacional do Prumo para reduzir overhead de contexto sem
  perder historico. Use com /prumo:sanitize.
---

# Sanitização Operacional (Prumo)

Use este fluxo para manter arquivos de estado enxutos.

## Passo 1: Pré-checagem

1. Ler `PRUMO-CORE.md` e validar lock em `_state/agent-lock.json`.
2. Confirmar existência de `_state/HANDOVER.md`.
3. Se necessário, consultar `references/sanitization.md` para regras detalhadas de compactação e thresholds.

## Passo 2: Simulação (dry-run)

1. Executar:
   - `if [ -f scripts/prumo_sanitize_state.py ]; then python3 scripts/prumo_sanitize_state.py --workspace .; elif [ -f Prumo/cowork-plugin/scripts/prumo_sanitize_state.py ]; then python3 Prumo/cowork-plugin/scripts/prumo_sanitize_state.py --workspace .; else python3 Prumo/scripts/prumo_sanitize_state.py --workspace .; fi`
   - opcional (gatilhos automáticos + calibração por workspace): `if [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace .; elif [ -f Prumo/cowork-plugin/scripts/prumo_auto_sanitize.py ]; then python3 Prumo/cowork-plugin/scripts/prumo_auto_sanitize.py --workspace .; else python3 Prumo/scripts/prumo_auto_sanitize.py --workspace .; fi`
2. Reportar ao usuário quantos handovers `CLOSED` podem ser movidos para archive.

## Passo 3: Aplicação

1. Se o usuário confirmar, executar:
   - `if [ -f scripts/prumo_sanitize_state.py ]; then python3 scripts/prumo_sanitize_state.py --workspace . --apply; elif [ -f Prumo/cowork-plugin/scripts/prumo_sanitize_state.py ]; then python3 Prumo/cowork-plugin/scripts/prumo_sanitize_state.py --workspace . --apply; else python3 Prumo/scripts/prumo_sanitize_state.py --workspace . --apply; fi`
   - opcional (automático): `if [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace . --apply; elif [ -f Prumo/cowork-plugin/scripts/prumo_auto_sanitize.py ]; then python3 Prumo/cowork-plugin/scripts/prumo_auto_sanitize.py --workspace . --apply; else python3 Prumo/scripts/prumo_auto_sanitize.py --workspace . --apply; fi`
2. Confirmar arquivos gerados/atualizados:
   - `_state/archive/backups/HANDOVER.md.<timestamp>`
   - `_state/archive/HANDOVER-ARCHIVE.md` (quando houver itens movidos)
   - `_state/HANDOVER.md`
   - `_state/HANDOVER.summary.md`
   - `_state/auto-sanitize-state.json`
   - `_state/auto-sanitize-history.json`

## Passo 4: Pós-checagem

1. Informar resumo objetivo:
   - total de handovers no ativo,
   - quantos foram arquivados,
   - próximos passos sugeridos (se houver).
2. Não editar arquivos pessoais (`CLAUDE.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`).
3. Se o usuário estiver pedindo limpeza/revisão do `CLAUDE.md`, interromper este fluxo e redirecionar para `/higiene`.
