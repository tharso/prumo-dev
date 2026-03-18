# Plano de migração do plugin Prumo (pós-4.1.0)

Data de criação: 03/03/2026  
Branch de preparo: `codex/fase2-fase3-prep`  
Objetivo: concluir alinhamento estrutural do Prumo com o padrão observado nos plugins oficiais, sem quebrar slash commands e sem regressão de briefing/inbox.

## Estado atual (já entregue)

- Fase 1 concluída em `4.1.0`: camada `commands/` criada e comandos do Prumo disponíveis no autocomplete.
- Comandos ativos no pacote: `setup`, `prumo` (alias legado), `briefing`, `handover`, `sanitize`, `start`.
- Marketplace e manifests já compatíveis com distribuição atual.

## Estratégia de execução

Não misturar hipóteses na mesma mudança. A sequência obrigatória é:

1. Fase 2: remover campo `"skills"` do `plugin.json`, mantendo estrutura física atual.
2. Validar comportamento no Cowork.
3. Fase 3: mover `cowork-plugin/skills/` para `skills/` na raiz.
4. Validar novamente no Cowork.

Se falhar em qualquer fase, rollback imediato para o estado anterior estável.

## Fase 2: remover `"skills"` do manifest

### Escopo

- Arquivos-alvo:
  - `plugin.json`
  - `.claude-plugin/plugin.json`
- Remover apenas a chave `"skills"` e manter metadados restantes.
- Não mover diretórios.
- Não alterar `commands/`.

### Checklist técnico

1. Atualizar versão para `4.1.1`.
2. Sincronizar versão em:
   - `VERSION`
   - `cowork-plugin/VERSION`
   - `plugin.json`
   - `.claude-plugin/plugin.json`
   - `marketplace.json`
   - `.claude-plugin/marketplace.json`
3. Atualizar `CHANGELOG.md`.
4. Rodar validações:
   - `claude plugin validate marketplace.json`
   - `claude plugin validate .claude-plugin/marketplace.json`
   - `claude plugin validate plugin.json`
   - `claude plugin validate .claude-plugin/plugin.json`
   - `bash cowork-plugin/scripts/tests/briefing_smoke.sh`

### Critério de aceite

- `/prumo:*` continua aparecendo no autocomplete.
- `/prumo:briefing` executa normalmente.
- Skills continuam disponíveis no `system-reminder`.

### Rollback

Reintroduzir `"skills"` nos dois `plugin.json`, bump de patch (`4.1.2`) e reinstalação.

## Fase 3: mover skills para `skills/` na raiz

### Escopo

- Mover:
  - `cowork-plugin/skills/prumo` → `skills/prumo`
  - `cowork-plugin/skills/briefing` → `skills/briefing`
  - `cowork-plugin/skills/handover` → `skills/handover`
  - `cowork-plugin/skills/sanitize` → `skills/sanitize`
  - `cowork-plugin/skills/start` → `skills/start`
- Atualizar paths em:
  - `commands/*.md`
  - referências cruzadas de skills
  - rotas de update do core (`prumo-core` e `briefing`)

### Checklist técnico

1. Criar branch dedicada da fase: `codex/fase3-skills-root`.
2. Atualizar versão para `4.2.0`.
3. Ajustar todos os links relativos para `../skills/...`.
4. Rodar validações de manifest + smoke test.
5. Validar instalação limpa no Cowork (marketplace URL).

### Critério de aceite

- Autocomplete mantém os comandos do Prumo.
- Execução dos 6 comandos passa em sessão nova.
- Briefing mantém:
  - update check do core
  - geração de preview
  - atualização de `_state/briefing-state.json`
  - leitura de handover sem falso pendente.

### Rollback

Reverter movimento de diretórios, restaurar paths antigos, lançar patch de correção.

## Protocolo de validação no Cowork (após cada fase)

1. Fechar o app Cowork.
2. Reabrir o app.
3. Abrir conversa nova.
4. Testar:
   - `/prumo:setup`
   - `/prumo:prumo`
   - `/prumo:briefing`
   - `/prumo:handover`
   - `/prumo:sanitize`
   - `/prumo:higiene`
   - `/prumo:start`
5. Registrar resultado com data/hora no handover da rodada.

## Governança de mudança

- Uma fase por PR.
- Um objetivo por release.
- Sem “mega-PR” misturando manifest, estrutura e runtime.

## Dependências abertas

- Confirmar comportamento de autocomplete global do Cowork (itens cinza fora do prefixo) como limitação de UI, não bug do Prumo.
- Planejar limpeza de pacote distribuído (remoção de `.git/`) em rodada separada para não contaminar Fase 2/3.
