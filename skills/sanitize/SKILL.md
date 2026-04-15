---
name: sanitize
description: >
  Compacta estado operacional (handovers). Se o pedido for limpeza
  de arquivos do workspace, use /faxina. Se for revisão assistida
  de conteúdo pessoal, use /higiene.
---

# Sanitização Operacional

O sanitize cuida de estado técnico do Prumo — especificamente,
handovers antigos que pesam o contexto.

Para limpeza geral do workspace (registro, índices, inbox), use `/faxina`.
Para revisão assistida de conteúdo pessoal (pauta velha, contradições,
CLAUDE.md pesado), use `/higiene`.

## O que o sanitize faz

1. Compacta `.prumo/state/HANDOVER.md` — arquiva handovers CLOSED antigos
2. Gera `.prumo/state/HANDOVER.summary.md` — versão leve pro briefing
3. Mantém `.prumo/state/archive/ARCHIVE-INDEX.json` — rastreabilidade

## Como rodar

Se houver shell:

```bash
python3 scripts/prumo_sanitize_state.py --workspace .          # dry-run
python3 scripts/prumo_sanitize_state.py --workspace . --apply   # aplicar
```

Auto-sanitize (com cooldown e thresholds adaptativos):

```bash
python3 scripts/prumo_auto_sanitize.py --workspace .
python3 scripts/prumo_auto_sanitize.py --workspace . --apply
```

Consultar `references/sanitization.md` para regras detalhadas.

## Regras

- Nunca toca em arquivos pessoais (CLAUDE.md, PAUTA.md, INBOX.md, etc.)
- Backup antes de qualquer compactação
- Se o pedido for limpeza de CLAUDE.md → redirecionar pra `/higiene`
- Se o pedido for limpeza geral de arquivos → redirecionar pra `/faxina`
