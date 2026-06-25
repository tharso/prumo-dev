# Perfil Hygiene

> **module_version: 4.18.0**
>
> Fonte canônica da higiene assistida do `Prumo/Agente/PERFIL.md` e dos módulos do `Agente/`.

## Princípio

`Prumo/Agente/PERFIL.md` e os módulos do `Agente/` (em especial o `ROTINA.md`) são configuração viva do usuário. Não entram em autosanitização.

Higiene aqui significa:

1. diagnosticar duplicações, redundâncias e conflitos;
2. propor limpeza;
3. só aplicar com confirmação explícita do usuário.

## Procedimento

### Passo 1: Ler contexto

1. Ler `Prumo/Agente/PERFIL.md` e `Prumo/Agente/ROTINA.md`.
2. Ler `.prumo/system/PRUMO-CORE.md`.
3. Ler `runtime-file-governance.md`.
4. Se houver shell, ler `runtime-paths.md`.

### Passo 2: Rodar diagnóstico

A higiene é conduzida pelo **agente**: ler os arquivos do escopo (`PERFIL.md` e módulos do `Agente/`) e diagnosticar à mão, comparando com o contrato de `runtime-file-governance.md`. Há uma referência histórica a um script `prumo_claude_hygiene.py` que **não existe na arquitetura atual** (vivia em `cowork-plugin/`, removido na consolidação skills-first) — **não depender dele**; o diagnóstico e a proposta são do agente.

O diagnóstico deve gerar:

1. relatório JSON;
2. relatório Markdown;
3. patch proposto;
4. cópia proposta do `Prumo/Agente/PERFIL.md`.

Além da limpeza estrutural, o diagnóstico deve classificar drift de conteúdo:

1. pendência datada que parece pertencer a `PAUTA.md`;
2. registro histórico que parece pertencer a `REGISTRO.md` ou changelog;
3. status transitório velho demais para continuar em configuração viva;
4. item que exige confirmação factual antes de qualquer movimento;
5. **ritual recorrente no PERFIL** (seção "Lembretes recorrentes", modelo legado anterior à 5.9) → propor migração por natureza: com hora → **agenda** (seguir `escrita-calendario.md`: oferecer, idempotência, série recorrente, tombstone no REGISTRO); sem hora → **`Agente/ROTINA.md`**; sem mudar nenhuma decisão → **poda**;
6. **redundância no `ROTINA.md`**: linha duplicada; **histórico de ocorrências disfarçado de padrão** ("segunda fiz X, terça fiz X, quarta fiz X" — o `ROTINA` guarda o *padrão estável*, não o log do que aconteceu); ritual com hora que deveria estar só na agenda (exclusividade — não duplicar no ROTINA); ou contexto que não muda decisão nenhuma (candidato a poda).

Destino padrão:

- `.prumo/state/perfil-hygiene/perfil-hygiene-report.json`
- `.prumo/state/perfil-hygiene/perfil-hygiene-report.md`
- `.prumo/state/perfil-hygiene/perfil-hygiene.patch`
- `.prumo/state/perfil-hygiene/PERFIL.proposed.md`

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

Se o usuário aprovar explicitamente, **nesta ordem** (backup antes de mudar):

1. **backup primeiro** — copiar para `.prumo/backups/perfil-hygiene/<YYYYMMDDTHHMMSS>/` **todos** os arquivos que a mudança vai tocar, não só o `PERFIL.md`: se a migração move ritual para o `ROTINA.md`, fazer backup do `ROTINA.md` também (o destino também é cirurgia);
2. aplicar a mudança proposta;
3. atualizar `REGISTRO.md`.

## Guardrails

1. `Prumo/Agente/PERFIL.md` nunca entra em autosanitização.
2. Sem confirmação explícita, nada é escrito no arquivo.
3. Se o diagnóstico não encontrar mudança segura, o arquivo fica como está.
4. Conflitos potenciais podem ser reportados sem serem resolvidos automaticamente.
5. Conteúdo no arquivo errado deve virar sugestão de destino, não mudança silenciosa.
6. Se o `.prumo/system/PRUMO-CORE.md` do workspace estiver atrás da versão do runtime, isso deve aparecer no relatório como observação de governança.
