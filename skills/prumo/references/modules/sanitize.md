# Sanitização de sistema (módulo do core)

> Era a skill top-level `sanitize` até a 5.31 — a #172 tirou a manutenção
> técnica do picker. Roda quando o `/fim` detecta acúmulo e o usuário topa,
> ou a pedido ("sanitiza o estado técnico", "o .prumo tá pesado").

Objetivo: manter o território técnico do Prumo (`.prumo/`) enxuto sem apagar histórico.

Escopo **exclusivo**: `.prumo/` (e o legado flat `_state/`) — nunca tocar em arquivos pessoais do usuário; backup antes de qualquer remoção que não seja redundância. Se o pedido for limpeza do workspace (registro, índices, inbox) → faxina (`faxina.md`, neste diretório). Se for revisão assistida de conteúdo pessoal (pauta velha, contradições, PERFIL pesado) → `/higiene`.

## Procedimento (com runtime — caminho preferido, #179)

O motor determinístico é o subcomando do runtime. Sempre em três passos:

1. **Dry-run** (read-only) com o relatório salvo — ele é o plano:
   `prumo sanitize --workspace . --format json > plano-sanitize.json`.
   Apresentar ao usuário os totais **por regra** (contagem + bytes), com os
   itens mais pesados como exemplo. Nada foi tocado ainda.
2. **Aprovação e aplicação do plano**: colher o sim do usuário — pode ser
   seletivo ("HANDOVERs sim, cache não"). Executar entregando o plano
   aprovado: `prumo sanitize --workspace . --apply --plan plano-sanitize.json
   --rules handover_legacy --yes` (sem `--rules` aplica todas as regras DO
   PLANO; `--rules` filtra o plano, nunca o expande — e `--rules` vazio é
   erro, não "tudo"). O `--yes` é a aprovação colhida; sem ele — ou sem
   `--plan` — o comando recusa. **Só executa o que está no plano**: item que
   surgiu, mudou ou sumiu desde a aprovação fica `blocked`.
3. Reportar o resultado: movidos (e o backup único em
   `.prumo/backups/sanitize/<stamp>/`, com o journal `SANITIZE-JOURNAL.json`
   dentro), removidos, bloqueados (não é erro — é proteção; re-rodar o
   dry-run e re-aprovar).

## Regras do motor (o que cada uma faz)

| Regra | Detecção | Ação |
|---|---|---|
| `handover_legacy` | `HANDOVER*` sob `.prumo/state/**` e `_state/**` (formato aposentado, #68) | move → backup |
| `decidir_ephemeral` | HTML/fonte em `.prumo/state/decidir` e `.prumo/state/acervo` com idade > 14d (#102: reproduzíveis) | move → backup |
| `agente_rascunho` | Filho DIRETO de `.prumo/state/rascunho/` — no layout flat, `_state/rascunho/` — com idade > 14d (#263). Diretório sai inteiro, e só com a árvore toda fria — varrer arquivo a arquivo desmontaria uma reconstrução parcial. Subtree **exclusiva**: nenhuma outra regra a reivindica, nem quando rodada isolada. Árvore que carrega `backup(s)` fica onde está (regra de ouro da #178) | move → backup |
| `nested_backups` | diretório de backup DENTRO de um backup root (`.prumo/`, `backups/`, `backup/`) | remove (redundância) |
| `expired_backups` | backup com idade > 90d (canônico e legados) | remove (expirado não ganha backup) |
| `legacy_backup_consolidation` | sobreviventes de `.prumo/backup/` singular (pré-#81) | move → `.prumo/backups/legacy/` |
| `workspace_cache` | `.prumo/cache/**` com idade > 30d | remove (reproduzível) |
| `asset_dedupe` | fonte em `.prumo/state/**` com SHA-256 idêntico à vendored em `.prumo/skills/**/assets/` e sem HTML vivo referenciando | remove (a vendored é o backup) |

Fora do motor (exige julgamento, segue manual): arquivos de estado em
`.prumo/state/` que cresceram além do razoável → propor mover excedente para
`.prumo/state/archive/` com registro no índice, caso a caso.

## Procedimento manual (fallback sem runtime)

Mesmas regras da tabela acima, na mão e com a mesma disciplina: dry-run
(listar candidatos por regra, com idade e tamanho) → aprovação → aplicar
somente o que foi listado e aprovado. Movimentos vão para
`.prumo/backups/sanitize/<stamp>/` com o path achatado
(`_state/HANDOVER.md` → `_state__HANDOVER.md`); se o nome achatado já
existir no destino, não sobrescrever — pular e reportar (o mapa origem →
destino autoritativo é o registro no índice, não o nome). Remoções só para
as regras de redundância (aninhados, expirados, cache, fonte duplicada com
hash conferido). Nunca copiar diretório de backup pra dentro de backup.

## Registro

Todo movimento entra nos índices, com **paths relativos** ao workspace:

- `.prumo/state/archive/ARCHIVE-INDEX.json`
- `.prumo/state/archive/ARCHIVE-INDEX.md`

## Segurança

1. Escopo exclusivo é `.prumo/` (+ `_state/` legado). Nunca toca em arquivos pessoais do usuário — caches de plugin do HOST (`~/.claude/plugins/...`) são território do **doctor** (reporta com comando pronto), nunca do sanitize.
2. Sempre dry-run antes de aplicar; `--apply` sem `--plan` (o relatório aprovado) ou sem `--yes` recusa. O apply executa exatamente o plano: divergência entre o aprovado e o estado atual vira `blocked`.
3. Não remove histórico: HANDOVERs e efêmeros movem pra backup (90d de recuperação); só redundância comprovada (backup de backup, expirado, cache, hash duplicado) é removida de verdade.
4. Não altera `PERFIL.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`.
5. Preserva `workspace-schema.json`, `agent-lock.json` e `.prumo/logs/` — estado ativo do runtime não entra em sanitização.
6. Ao registrar movimentos em `ARCHIVE-INDEX.json`/`ARCHIVE-INDEX.md`, sempre usar paths relativos ao workspace. Path absoluto (`/Users/...`, `C:\...`) em qualquer arquivo de estado persistido é bug — viola o contrato de portabilidade (o motor levanta erro).
7. Arquivar frio só com política explícita (as regras acima) — nada de threshold inventado na hora.
8. Symlink nunca é candidato nem é atravessado — nem o próprio item, nem qualquer diretório no caminho até ele (enumerar, ler, hashear, mover e apagar exigem cadeia limpa dentro de `.prumo/`/`_state/`).
