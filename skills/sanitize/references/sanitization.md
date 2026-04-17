# Sanitização de sistema

Objetivo: manter o território técnico do Prumo (`.prumo/`) enxuto sem apagar histórico.

## Comando

- `if [ -f scripts/prumo_sanitize_state.py ]; then python3 scripts/prumo_sanitize_state.py --workspace . --apply; else python3 Prumo/scripts/prumo_sanitize_state.py --workspace . --apply; fi`
- `if [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace . --apply; else python3 Prumo/scripts/prumo_auto_sanitize.py --workspace . --apply; fi`
- `if [ -f scripts/prumo_auto_sanitize.py ]; then python3 scripts/prumo_auto_sanitize.py --workspace . --adaptive auto; else python3 Prumo/scripts/prumo_auto_sanitize.py --workspace . --adaptive auto; fi`

## O que faz

1. Remove backups em `.prumo/backups/` acima do threshold de idade (default: 90 dias).
2. Limpa cache expirado em `.prumo/cache/`.
3. Arquiva arquivos de estado em `.prumo/state/` que cresceram além de threshold, movendo o excedente para `.prumo/state/archive/`.
4. Registra qualquer movimento nos índices:
   - `.prumo/state/archive/ARCHIVE-INDEX.json`
   - `.prumo/state/archive/ARCHIVE-INDEX.md`
5. (auto) Aplica gatilhos por tamanho/volume e respeita cooldown para não rodar em loop.

## Gatilhos padrão (auto)

1. Backups em `.prumo/backups/` com idade > 90 dias.
2. Arquivos em `.prumo/cache/` com idade > threshold configurado.
3. Arquivos de estado em `.prumo/state/` acima de tamanho/linhas (definido por arquivo).
4. `Inbox4Mobile/` com itens processados antigos (ver `faxina` para gestão de inbox — sanitize só toca o que está em `.prumo/`).

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

1. Escopo exclusivo é `.prumo/`. Nunca toca em arquivos pessoais do usuário.
2. Sem `--apply`, roda em dry-run.
3. Não remove histórico; sempre move para archive antes de limpar.
4. Não altera `PERFIL.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`.
5. Preserva `briefing-state.json`, `workspace-schema.json` e `agent-lock.json` — estado ativo do runtime não entra em sanitização.
