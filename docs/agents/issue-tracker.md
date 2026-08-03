# Issue tracker: GitHub (`tharso/prumo-dev`)

Issues e PRDs deste repo vivem como issues do GitHub. Use o `gh` para todas as operações.

## Repo alvo — invariante

**Todo `gh` roda contra `tharso/prumo-dev`.** Nunca abrir issue, PR ou tag em `tharso/prumo` (repo público): ele é espelho gerado automaticamente pelo workflow `.github/workflows/mirror-to-prumo.yml`, e qualquer coisa empurrada direto lá é sobrescrita no próximo push do dev.

O `gh` infere o repo a partir do `git remote` quando roda dentro do clone — o que já resolve o caso normal. Se precisar de `--repo` explícito, é `tharso/prumo-dev`.

## Convenções

- **Criar issue**: `gh issue create --title "..." --body "..."`. Use heredoc para corpo multi-linha.
- **Ler issue**: `gh issue view <número> --comments`, filtrando comentários com `jq` e buscando também os labels.
- **Listar issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` com os filtros `--label` e `--state` apropriados.
- **Comentar**: `gh issue comment <número> --body "..."`
- **Aplicar / remover labels**: `gh issue edit <número> --add-label "..."` / `--remove-label "..."`
- **Fechar**: `gh issue close <número> --comment "..."`

## Política de issues

As regras de **quem cria, quem fecha e como assinar** moram no `CLAUDE.md`, seção "Issues e documentação" — inclusive a regra anti-zombie (comentário de conclusão obriga fechar na ação seguinte) e a distinção entre issue submetida pelo usuário e issue criada pelo agente. Este arquivo cobre a mecânica; a política é de lá.

## Pull requests como superfície de triagem

**PRs como superfície de pedido: não.** _(Mudar para `sim` se este repo passar a tratar PR externo como pedido de feature; a `/triage` lê esta flag.)_

Quando estiver em `sim`, PRs passam pelos mesmos labels e estados das issues, usando os equivalentes `gh pr`:

- **Ler um PR**: `gh pr view <número> --comments` e `gh pr diff <número>` para o diff.
- **Listar PRs externos para triagem**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` e manter só `authorAssociation` de `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR` ou `NONE` (descartar `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comentar / rotular / fechar**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

O GitHub compartilha um único espaço de numeração entre issues e PRs, então um `#42` solto pode ser qualquer um dos dois — resolva com `gh pr view 42` e caia para `gh issue view 42`.

## Quando uma skill disser "publicar no issue tracker"

Criar uma issue no GitHub, em `tharso/prumo-dev`.

## Quando uma skill disser "buscar o ticket relevante"

Rodar `gh issue view <número> --comments`.

## Operações de wayfinding

Usadas pela `/wayfinder`. O **mapa** é uma issue única com issues **filhas** como tickets.

- **Mapa**: uma issue com o label `wayfinder:map`, contendo o corpo Notas / Decisões-até-agora / Névoa. `gh issue create --label wayfinder:map`.
- **Ticket filho**: issue ligada ao mapa como sub-issue do GitHub (`gh api` no endpoint de sub-issues). Onde sub-issues não estiverem habilitadas, adicionar a filha a uma task list no corpo do mapa e colocar `Part of #<mapa>` no topo do corpo da filha. Labels: `wayfinder:<tipo>` (`research`/`prototype`/`grilling`/`task`). Depois de reivindicada, a issue é atribuída ao dev que a conduz.
- **Bloqueio**: **dependências nativas de issue** do GitHub — a representação canônica e visível na UI. Adicione uma aresta com `gh api --method POST repos/<owner>/<repo>/issues/<filha>/dependencies/blocked_by -F issue_id=<id-do-bloqueador>`, onde `<id-do-bloqueador>` é o **id numérico de banco** do bloqueador (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _não_ o `#número` nem o `node_id`). O GitHub reporta `issue_dependencies_summary.blocked_by` (só bloqueadores abertos — o portão vivo). Onde dependências não estiverem disponíveis, caia para uma linha `Blocked by: #<n>, #<n>` no topo do corpo da filha. Um ticket está desbloqueado quando todos os bloqueadores estão fechados.
- **Consulta de fronteira**: listar as filhas abertas do mapa (`gh issue list --state open`, no escopo das sub-issues / task list do mapa), descartar as que têm bloqueador aberto (`issue_dependencies_summary.blocked_by > 0`, ou uma issue aberta na linha `Blocked by`) ou responsável atribuído; a primeira na ordem do mapa vence.
- **Reivindicar**: `gh issue edit <n> --add-assignee @me` — a primeira escrita da sessão.
- **Resolver**: `gh issue comment <n> --body "<resposta>"`, depois `gh issue close <n>`, depois anexar um ponteiro de contexto (gist + link) às Decisões-até-agora do mapa.
