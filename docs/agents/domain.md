# Documentação de domínio

Como as skills de engenharia devem consumir a documentação de domínio deste repo ao explorar o codebase.

Este repo é **single-context**: um contexto só, sem monorepo, sem `CONTEXT-MAP.md`.

## Antes de explorar, ler

- **`CLAUDE.md`** na raiz — o contrato operacional. É a porta: as regras de comportamento estão lá, não aqui.
- **`DECISIONS.md`** na raiz — o log de decisões arquiteturais. **Não existe `docs/adr/` neste repo, e não deve ser criado.** Onde as skills falam em "ADRs", leia e escreva no `DECISIONS.md`.
- **`CONTEXT.md`** na raiz, se existir. Hoje não existe. Se não existir, **siga em silêncio** — não sinalize a ausência, não sugira criar. A `/domain-modeling` cria quando um termo de fato precisar ser resolvido.
- **`gotchas.md`** na raiz — padrões de erro já cometidos e convertidos em regra.

## Como ler o `DECISIONS.md`

O arquivo é grande (250 KB+) e tem **índice temático no topo**. Não confie em busca por palavra-chave ou por data: comece pelo índice, filtre pelo tópico da sua área e leia integralmente as entradas que ele apontar — o título de uma decisão frequentemente não revela o que ela decide.

O vocabulário controlado de tópicos está logo abaixo do índice. Tópico novo exige justificativa explícita na entrada que o introduz.

## Como escrever no `DECISIONS.md`

Antes de qualquer operação arquitetural — mudança de schema, contrato ou interface pública; dependency nova; mudança na API surface; refactor cross-file; renomear/mover/deletar pasta canônica; qualquer coisa que afete comportamento observável pelo usuário final — vale o **checklist de 6 passos** da seção "Antes de qualquer operação arquitetural" do `CLAUDE.md`. Ele é obrigatório e inclui declarar conflito ao dono **antes** de prosseguir.

O formato das entradas está definido no próprio `DECISIONS.md`, incluindo o campo obrigatório **"Relações com decisões anteriores"**. Toda entrada nova exige atualizar o índice temático do topo.

## Usar o vocabulário do projeto

Quando sua saída nomear um conceito de domínio (título de issue, proposta de refactor, hipótese, nome de teste), use o termo como o projeto já usa. Não derive para sinônimos.

Se o conceito que você precisa não existe no vocabulário, isso é sinal — ou você está inventando linguagem que o projeto não usa (reconsidere), ou há uma lacuna real (anote para a `/domain-modeling`).

## Sinalizar conflito com decisão existente

Se sua saída contradiz uma decisão já registrada, **declare explicitamente** em vez de sobrescrever em silêncio. O `CLAUDE.md` é categórico: nunca revogar silenciosamente uma decisão anterior.

> _Contradiz a decisão de 2026-04-14 (skills-first) — mas vale reabrir porque…_
