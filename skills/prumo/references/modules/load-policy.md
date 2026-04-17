# Load Policy

> **module_version: 4.17.0**
>
> Política canônica de leitura incremental do Prumo.

## Princípios

1. Ler primeiro o mínimo necessário para decidir.
2. Preferir resumo incremental quando disponível.
3. Abrir conteúdo pesado apenas quando houver necessidade objetiva de ação.

## Camadas

1. **Base (sempre):**
   - `Prumo/Agente/PERFIL.md`
   - `.prumo/system/PRUMO-CORE.md`
   - `PAUTA.md`
   - `INBOX.md`
2. **Leve (preferencial):**
   - `Inbox4Mobile/_preview-index.json`
   - `Inbox4Mobile/inbox-preview.html`
   - Gmail MCP / Calendar MCP direto
3. **Profunda (sob demanda):**
   - binários e arquivos longos
   - transcrições extensas

## Heurística de aprofundamento

Abrir bruto imediatamente se qualquer condição for verdadeira:

1. risco legal, financeiro ou documental;
2. vencimento em até 72h;
3. item `P1`;
4. ambiguidade que impeça ação segura.
