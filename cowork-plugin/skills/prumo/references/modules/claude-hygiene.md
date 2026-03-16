# Claude Hygiene

> **module_version: 4.5.0**
>
> Fonte canônica da higiene assistida do `CLAUDE.md`.

## Princípio

`CLAUDE.md` é configuração viva do usuário. Não entra em autosanitização.

Higiene aqui significa:

1. diagnosticar duplicações, redundâncias e conflitos;
2. propor limpeza;
3. só aplicar com confirmação explícita do usuário.

## Procedimento

### Passo 1: Ler contexto

1. Ler `CLAUDE.md`.
2. Ler `PRUMO-CORE.md`.
3. Se houver shell, ler `runtime-paths.md`.

### Passo 2: Rodar diagnóstico

Quando houver shell, usar `prumo_claude_hygiene.py` resolvendo os caminhos pela ordem definida em `runtime-paths.md`.

O diagnóstico deve gerar:

1. relatório JSON;
2. relatório Markdown;
3. patch proposto;
4. cópia proposta do `CLAUDE.md`.

Destino padrão:

- `_state/claude-hygiene/claude-hygiene-report.json`
- `_state/claude-hygiene/claude-hygiene-report.md`
- `_state/claude-hygiene/claude-hygiene.patch`
- `_state/claude-hygiene/CLAUDE.proposed.md`

### Passo 3: Mostrar proposta

Apresentar ao usuário:

1. categorias dos achados;
2. impacto esperado;
3. se a proposta altera ou não o arquivo.

Nunca aplicar direto.

### Passo 4: Aplicar só com confirmação

Se o usuário aprovar explicitamente:

1. rodar o script com `--apply`;
2. criar backup em `_backup/CLAUDE.md.YYYY-MM-DD-HHMMSS`;
3. atualizar `REGISTRO.md`.

## Guardrails

1. `CLAUDE.md` nunca entra em autosanitização.
2. Sem confirmação explícita, nada é escrito no arquivo.
3. Se o diagnóstico não encontrar mudança segura, o arquivo fica como está.
4. Conflitos potenciais podem ser reportados sem serem resolvidos automaticamente.
