# Multiagent

> **module_version: 4.20.0**
>
> Fonte canônica da convivência entre agentes no Prumo.
> Escopo: coordenação de escrita simultânea em estado compartilhado via lock.
>
> **Delegação a subagente:** subagente não herda este módulo nem o `AGENT.md` — o perímetro de leitura viaja no prompt da delegação (caminhos permitidos explícitos, sem enumeração fora deles). Regra e exemplo canônico em `load-policy.md` → "Listagem de diretórios".

## Princípios

1. Cooperação explícita, não competição.
2. Um agente altera estado por vez em cada escopo crítico.
3. Lock é infraestrutura: existe pra evitar corrida, não pra documentar trabalho.

## Arquivo de estado

- `.prumo/state/agent-lock.json`

## Lock

Campos mínimos:

- `owner`
- `scope`
- `started_at`
- `ttl_minutes`

Regras:

1. sem lock ativo no escopo, o agente pode operar;
2. com lock ativo de outro agente, não escrever;
3. lock expirado pode ser assumido, registrando o motivo em nota curta.

## Quando usar lock

Casos em que faz sentido segurar lock antes de escrever:

1. mudança no `.prumo/system/PRUMO-CORE.md`;
2. mudança estrutural em arquivos do `Prumo/Agente/`;
3. operação longa que toca múltiplos arquivos do workspace.

Operações rápidas e locais (atualizar PAUTA.md, registrar no REGISTRO.md) não precisam de lock.

## Escopo com aquisição ATÔMICA (#244)

> Emenda ao contrato da #68 (coordenação por `agent-lock.json`): para **um escopo nomeado** — o índice de referências — o lock cooperativo não basta, e a primitiva abaixo passa a valer. O `agent-lock.json` segue sendo o mecanismo de coordenação para todo o resto.

O `agent-lock.json` acima é **cooperativo**: bom pra evitar atropelo, insuficiente pra garantir unicidade (ler-e-escrever tem janela; duas sessões passam pelo mesmo buraco). Onde a corrida corrompe dado — hoje **um escopo: `Prumo/Referencias/INDICE.md`**, cujo ID sequencial não admite duplicata —, o lock é adquirido por operação **atômica do filesystem**:

0. **Garantir os pais** (o setup cria `.prumo/state/`, não as subpastas do lock): `mkdir -p .prumo/state/locks/released` — idempotente, não é a trava.
1. **Com shell:** `mkdir '.prumo/state/locks/referencias-indice.d'` — a folha, **sem `-p`**: falha se já existe, e é isso que dá a exclusão sem janela.
2. **Sem shell:** **não escrever**. Dizer em uma linha que a alocação fica pra uma sessão com shell — ID adivinhado é o bug que a #244 corrigiu. (Um comando de runtime com `O_CREAT|O_EXCL` daria a mesma garantia, mas **não existe hoje** — prometer caminho inexistente é pior que não ter caminho.)

**Liberação: mover, nunca deletar** — `mv .prumo/state/locks/referencias-indice.d .prumo/state/locks/released/<AAAA-MM-DDTHH-MM-SS>`. Deleção não é operação do produto (#242) e, no host que a proíbe, liberar por `rmdir` deixaria o índice travado **pra sempre**. Destino existente nunca é sobrescrito: checar o path candidato direto (sem listar) e, se ocupado, sufixo determinístico (`-2`, `-3`, …), a mesma regra da quarentena.

**Sem retomada automática por idade.** Lock presente = abortar e avisar, com a linha pronta pro usuário liberar se souber que ninguém mais está mexendo. Heurística de "lock velho" reintroduz exatamente a corrida que o lock existe pra matar.
