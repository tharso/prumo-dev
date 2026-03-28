# Load Policy

> **module_version: 4.16.6**
>
> Política canônica de leitura incremental do Prumo.
>
> A partir de 2026-03-28, a casa canônica compartilhada passou a ser `Prumo/canon/governance/load-policy.md`. Este arquivo permanece como espelho legado enquanto o bundle antigo ainda respira.

## Princípios

1. Ler primeiro o mínimo necessário para decidir.
2. Preferir resumo incremental quando disponível.
3. Abrir conteúdo pesado apenas quando houver necessidade objetiva de ação.

## Camadas

1. **Base (sempre):**
   - `CLAUDE.md`
   - `PRUMO-CORE.md`
   - `PAUTA.md`
   - `INBOX.md`
2. **Leve (preferencial):**
   - `_state/HANDOVER.summary.md`
   - `Inbox4Mobile/_preview-index.json`
   - `Inbox4Mobile/inbox-preview.html`
   - Google Docs `Prumo/snapshots/email-snapshot`
3. **Profunda (sob demanda):**
   - `_state/HANDOVER.md`
   - binários e arquivos longos
   - transcrições extensas

## Heurística de aprofundamento

Abrir bruto imediatamente se qualquer condição for verdadeira:

1. risco legal, financeiro ou documental;
2. vencimento em até 72h;
3. item `P1`;
4. ambiguidade que impeça ação segura.
