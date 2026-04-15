# Sanitização Operacional

Objetivo: manter arquivos operacionais enxutos sem apagar histórico.

## Comando

- `if [ -f scripts/prumo_sanitize_state.py ]; then python3 scripts/prumo_sanitize_state.py --workspace . --apply; elif [ -f scripts/prumo_sanitize_state.py ]; then python3 scripts/prumo_sanitize_state.py --workspace . --apply; else python3 Prumo/scripts/prumo_sanitize_state.py --workspace . --apply; fi`
- `if [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace . --apply; elif [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace . --apply; else python3 Prumo/scripts/prumo_auto_sanitize.py --workspace . --apply; fi`
- `if [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace . --adaptive auto; elif [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace . --adaptive auto; else python3 Prumo/scripts/prumo_auto_sanitize.py --workspace . --adaptive auto; fi`

## O que faz

1. Compacta `.prumo/state/HANDOVER.md` mantendo apenas handovers `CLOSED` recentes.
2. Move handovers antigos para `.prumo/state/archive/HANDOVER-ARCHIVE.md`.
3. Gera backup antes de escrever: `.prumo/state/archive/backups/HANDOVER.md.<timestamp>`.
4. Gera `.prumo/state/HANDOVER.summary.md` para leitura leve no briefing.
5. (auto) Aplica gatilhos por tamanho/volume e respeita cooldown para não rodar em loop.

## Gatilhos padrão (auto)

1. `HANDOVER.md` com tamanho >= `120000` bytes ou >= `350` linhas, com `CLOSED` acima de `handover_keep_closed`.
2. `Inbox4Mobile/` com >= `8` arquivos totais ou >= `4` itens multimídia.
3. `inbox-preview.html` / `_preview-index.json` ausentes ou defasados em relação ao arquivo mais novo do inbox.

## Estado persistido (auto)

`.prumo/state/auto-sanitize-state.json` guarda:

1. `last_run_at` e `last_apply_at`
2. métricas observadas
3. thresholds em uso
4. decisão (`triggers`, `cooldown_ok`, `will_apply`)
5. resultado de cada ação executada

Histórico por workspace (base para calibração adaptativa):

- `.prumo/state/auto-sanitize-history.json`

## Segurança

1. Sem `--apply`, roda em dry-run.
2. Não remove histórico; apenas move para arquivo de archive.
3. Não altera `PERFIL.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`.
