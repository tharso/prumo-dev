# Template do Prumo/AGENT.md (fonte canônica)

> Este template gera o arquivo `Prumo/AGENT.md` — a fonte canônica do workspace.
> É o primeiro arquivo que qualquer agente deve ler. Todos os ponteiros
> da raiz (CLAUDE.md, AGENT.md, AGENTS.md) apontam pra cá.
>
> O agente de setup deve preencher os placeholders `{{VARIAVEL}}` e resolver
> as seções condicionais. O resultado NÃO deve conter nenhum placeholder.
>
> A tabela de fallback mapeia cada comando à skill correspondente no workspace.
> Se o runtime CLI não estiver disponível, o agente lê a skill direto.

---

INÍCIO DO TEMPLATE:

---

# AGENT.md

> Arquivo canônico de navegação do workspace de {{USER_NAME}}.
> Se você é um agente, comece aqui.

## Identidade rápida

- Nome preferido do usuário: {{USER_NAME}}
- Nome do agente: {{AGENT_NAME}}
- Fuso: {{TIMEZONE}}
- Briefing preferencial: {{BRIEFING_TIME}}

## Cadeia de resolução de comandos

Ordem de tentativa: slash command → runtime CLI → skill direto.

Se o slash command não funcionar, tentar `prumo <comando>` no terminal.
Se o runtime não estiver no PATH, ler a skill correspondente no workspace:

| Comando | Skill |
|---|---|
| briefing | `Prumo/skills/briefing/SKILL.md` |
| setup | `Prumo/skills/prumo/SKILL.md` |
| start | `Prumo/skills/start/SKILL.md` |
| faxina | `Prumo/skills/faxina/SKILL.md` |
| higiene | `Prumo/skills/higiene/SKILL.md` |
| sanitize | `Prumo/skills/sanitize/SKILL.md` |
| doctor | `Prumo/skills/doctor/SKILL.md` |

## Ler nesta ordem

1. `Prumo/Agente/INDEX.md`
2. `Prumo/Agente/PERFIL.md`
3. `Prumo/PAUTA.md`
4. `Prumo/INBOX.md`
5. `.prumo/system/PRUMO-CORE.md`
6. `Prumo/REGISTRO.md` (quando precisar histórico)

## Mapa do workspace

- `Prumo/Agente/`: contexto modular do usuário (perfil, pessoas, índice)
- `Prumo/PAUTA.md`: estado vivo e pendências
- `Prumo/INBOX.md`: itens ainda não processados
- `Prumo/REGISTRO.md`: rastro do que aconteceu
- `Prumo/IDEIAS.md`: ideias sem ação imediata
- `Prumo/Referencias/`: material de referência
- `Prumo/Inbox4Mobile/`: captura mobile
- `Prumo/skills/`: skills do Prumo (portáveis, lidas diretamente quando CLI não estiver disponível)
- `.prumo/system/PRUMO-CORE.md`: regras do motor e guardrails do sistema
- `.prumo/state/`: estado técnico e metadados do runtime
- `.prumo/logs/`: registros de revisão

## Regras rápidas

1. Tudo que é do usuário continua legível sem o Prumo.
2. `CLAUDE.md`, `AGENT.md` e `AGENTS.md` na raiz são ponteiros de compatibilidade, não a fonte de verdade.
3. Se um arquivo modular faltar, avisar antes de inventar realidade.
4. Se o usuário chamar "Prumo", "bom dia, Prumo" ou equivalente, tentar rodar `prumo` no diretório do workspace.
5. Se `prumo` não estiver no PATH, tentar `$HOME/.local/bin/prumo` antes de concluir que o runtime sumiu.
6. Se o runtime não existir, usar a cadeia de fallback (skill direto). Isso é operação legítima, não simulação.
7. Não escrever arquivos em `.prumo/state/` fingindo ser o runtime.
