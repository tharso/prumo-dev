---
name: sanitize
description: >
  Compacta estado técnico do sistema (backups velhos, cache expirado,
  arquivos de estado que crescem demais em .prumo/). Se o pedido for
  limpeza de arquivos do workspace do usuário, use /faxina. Se for
  revisão assistida de conteúdo pessoal, use /higiene.
---

# Sanitização de sistema

O sanitize cuida do território técnico do Prumo. Escopo exclusivo: `.prumo/`.

Para limpeza geral do workspace (registro, índices, inbox), use `/faxina`.
Para revisão assistida de conteúdo pessoal (pauta velha, contradições,
PERFIL.md pesado), use `/higiene`.

## O que o sanitize faz

1. Remove backups antigos de `.prumo/backups/` (> 90 dias)
2. Limpa cache expirado de `.prumo/cache/`
3. Arquiva arquivos de estado em `.prumo/state/` que crescerem além de threshold
4. Registra qualquer movimento em `.prumo/state/archive/ARCHIVE-INDEX.json`

## Como rodar

Sanitize hoje é procedimento que o agente executa manualmente seguindo as regras de `references/sanitization.md`. Quando o runtime do Prumo for oferecer um subcomando dedicado, este documento ganha a chamada correspondente.

O fluxo padrão é dry-run primeiro (listar candidatos sem tocar em nada), aprovação do usuário, depois aplicação com backup.

Consultar `references/sanitization.md` para regras detalhadas.

## Regras

- Escopo exclusivo é `.prumo/`. Nunca tocar em arquivos pessoais do usuário.
- Backup antes de qualquer remoção ou arquivamento.
- Se o pedido for limpeza de CLAUDE.md, PERFIL.md ou PAUTA.md → redirecionar pra `/higiene`.
- Se o pedido for limpeza de registro, inbox ou índices → redirecionar pra `/faxina`.
