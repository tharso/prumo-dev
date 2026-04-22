# Sanitização de sistema

Objetivo: manter o território técnico do Prumo (`.prumo/`) enxuto sem apagar histórico.

## Procedimento

Sanitize é executado pelo agente seguindo as regras abaixo. Roda sempre em dois passos: dry-run (listar candidatos, reportar ao usuário) e, após aprovação, aplicação com backup. Quando o runtime do Prumo oferecer um subcomando dedicado, este documento ganha a chamada correspondente.

## O que faz

1. Remove backups em `.prumo/backups/` acima do threshold de idade (default: 90 dias).
2. Limpa cache expirado em `.prumo/cache/`.
3. Arquiva arquivos de estado em `.prumo/state/` que cresceram além de threshold, movendo o excedente para `.prumo/state/archive/`.
4. Registra qualquer movimento nos índices:
   - `.prumo/state/archive/ARCHIVE-INDEX.json`
   - `.prumo/state/archive/ARCHIVE-INDEX.md`
## Gatilhos padrão

1. Backups em `.prumo/backups/` com idade > 90 dias.
2. Arquivos em `.prumo/cache/` com idade > threshold configurado.
3. Arquivos de estado em `.prumo/state/` acima de tamanho/linhas (definido por arquivo).
4. `Inbox4Mobile/` com itens processados antigos (ver `faxina` para gestão de inbox — sanitize só toca o que está em `.prumo/`).

## Segurança

1. Escopo exclusivo é `.prumo/`. Nunca toca em arquivos pessoais do usuário.
2. Sempre dry-run antes de aplicar.
3. Não remove histórico; sempre move para archive antes de limpar.
4. Não altera `PERFIL.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`.
5. Preserva `workspace-schema.json` e `agent-lock.json` — estado ativo do runtime não entra em sanitização.
