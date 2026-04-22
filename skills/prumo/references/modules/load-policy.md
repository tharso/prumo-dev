# Load Policy

> **module_version: 5.1.1**
>
> Política canônica de leitura incremental do Prumo.

## Princípios

1. Ler primeiro o mínimo necessário para decidir.
2. Preferir resumo incremental quando disponível.
3. Abrir conteúdo pesado apenas quando houver necessidade objetiva de ação.
4. Abertura de sessão não é briefing. Ver `modules/dispatch.md`.

## Camadas

1. **Abertura (sempre, via `modules/dispatch.md`):**
   - `Prumo/AGENT.md`
   - `.prumo/system/PRUMO-CORE.md` — Parte 1
   - scan leve: cabeçalhos de `PAUTA.md` + últimas 5-10 linhas de `REGISTRO.md`
2. **Playbook (sob demanda, conforme intenção do usuário):**
   - `.prumo/system/PRUMO-CORE.md` — Parte 2
   - `Prumo/Agente/PERFIL.md`
   - `PAUTA.md` integral, `INBOX.md`, `REGISTRO.md` integral
   - demais módulos da tabela "Módulos canônicos" em `prumo-core.md`
3. **Leve (preferencial dentro de playbook):**
   - `Inbox4Mobile/_preview-index.json`
   - `Inbox4Mobile/inbox-preview.html`
   - Gmail MCP / Calendar MCP direto
4. **Profunda (sob demanda):**
   - binários e arquivos longos
   - transcrições extensas

## Heurística de aprofundamento

Abrir bruto imediatamente se qualquer condição for verdadeira:

1. risco legal, financeiro ou documental;
2. vencimento em até 72h;
3. item `P1`;
4. ambiguidade que impeça ação segura.
