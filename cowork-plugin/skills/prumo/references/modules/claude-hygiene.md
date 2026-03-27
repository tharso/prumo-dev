# Claude Hygiene

> **module_version: 4.16.6**
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
3. Ler `runtime-file-governance.md`.
4. Se houver shell, ler `runtime-paths.md`.

### Passo 2: Rodar diagnóstico

Quando houver shell, usar `prumo_claude_hygiene.py` resolvendo os caminhos pela ordem definida em `runtime-paths.md`.

O diagnóstico deve gerar:

1. relatório JSON;
2. relatório Markdown;
3. patch proposto;
4. cópia proposta do `CLAUDE.md`.

Além da limpeza estrutural, o diagnóstico deve classificar drift de conteúdo:

1. pendência datada que parece pertencer a `PAUTA.md`;
2. registro histórico que parece pertencer a `REGISTRO.md` ou changelog;
3. status transitório velho demais para continuar em configuração viva;
4. item que exige confirmação factual antes de qualquer movimento.

Destino padrão:

- `_state/claude-hygiene/claude-hygiene-report.json`
- `_state/claude-hygiene/claude-hygiene-report.md`
- `_state/claude-hygiene/claude-hygiene.patch`
- `_state/claude-hygiene/CLAUDE.proposed.md`

### Passo 3: Mostrar proposta

Apresentar ao usuário:

1. `Mudanças seguras`;
2. `Itens que pedem confirmação factual`;
3. `Decisões de governança/arquitetura`;
4. impacto esperado;
5. se a proposta altera ou não o arquivo.
6. manter a numeração contínua entre esses blocos quando houver subitens no mesmo diagnóstico.
7. terminar, sempre que útil, com alternativas curtas para destravar a resposta do usuário.

Esses blocos não podem ser misturados. O produto precisa deixar claro o que é:

1. limpeza estrutural segura;
2. verdade factual pendente;
3. decisão de arquitetura do arquivo.

`Mudanças seguras` só inclui o que o patch atual consegue aplicar sem interpretar
qual cópia “merece” sobreviver ou para qual arquivo o conteúdo deve migrar.

Nunca aplicar direto.

Quando houver decisão para o usuário, preferir algo do tipo:

- `a) aplicar só as mudanças seguras`
- `b) responder os itens factuais`
- `c) revisar a governança antes`

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
5. Conteúdo no arquivo errado deve virar sugestão de destino, não mudança silenciosa.
6. Se o `PRUMO-CORE.md` do workspace estiver atrás da versão do runtime, isso deve aparecer no relatório como observação de governança.
