# Sanitization

> **module_version: 4.21.0**
>
> Fonte canônica de sanitização do estado técnico do sistema.
> Escopo: `.prumo/` — backups velhos, cache expirado, arquivos de estado que crescem demais.
> Nunca toca em arquivos pessoais do usuário.

## Execução

Sanitize é procedimento executado pelo agente seguindo as regras abaixo. Quando o runtime do Prumo oferecer um subcomando dedicado, esta seção ganha a chamada correspondente.

O fluxo é sempre em dois passos: dry-run (listar candidatos, reportar ao usuário) e, após aprovação, aplicação com backup.

O processo deve:

1. remover backups antigos de `.prumo/backups/` (> 90 dias);
2. limpar cache expirado de `.prumo/cache/`;
3. registrar qualquer movimento no índice global:
   - `.prumo/state/archive/ARCHIVE-INDEX.json`
   - `.prumo/state/archive/ARCHIVE-INDEX.md`
4. nunca tocar arquivos pessoais.

## Política

1. arquivar frio só com política explícita;
2. política inicial segura:
   - remoção de backups em `.prumo/backups/` acima do threshold de idade;
   - limpeza de cache expirado em `.prumo/cache/`;
   - arquivos de `Inbox4Mobile/` marcados como processados em `_processed.json` e acima do threshold de idade;
3. nunca apagar histórico sem archive;
4. nunca mover sem registrar no `ARCHIVE-INDEX`;
5. `PERFIL.md` está fora do escopo deste comando; para isso existe higiene assistida.
