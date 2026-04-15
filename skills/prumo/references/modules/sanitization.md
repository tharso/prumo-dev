# Sanitization

> **module_version: 4.17.0**
>
> Fonte canônica de sanitização manual e automática do estado operacional.

## Sanitização manual

Quando houver shell, usar `prumo_sanitize_state.py` resolvendo os caminhos pela ordem definida em `runtime-paths.md`.

O processo deve:

1. compactar handovers `CLOSED` antigos;
2. mover histórico para `.prumo/state/archive/HANDOVER-ARCHIVE.md`;
3. regenerar `.prumo/state/HANDOVER.summary.md`;
4. registrar movimentos no índice global:
   - `.prumo/state/archive/ARCHIVE-INDEX.json`
   - `.prumo/state/archive/ARCHIVE-INDEX.md`
5. nunca tocar arquivos pessoais.

## Autosanitização

Pode rodar no briefing como manutenção preventiva, não como ritual destrutivo.

Regras:

1. respeitar cooldown;
2. registrar estado em `.prumo/state/auto-sanitize-state.json`;
3. usar `.prumo/state/auto-sanitize-history.json` para calibrar thresholds quando houver amostra;
4. sem histórico suficiente, usar defaults seguros;
5. arquivar frio só com política explícita;
6. política inicial segura:
   - compactação de handovers `CLOSED`;
   - arquivos de `Inbox4Mobile/` marcados como processados em `_processed.json` e acima do threshold de idade;
7. nunca apagar histórico sem archive;
8. nunca mover sem registrar no `ARCHIVE-INDEX`.
9. `PERFIL.md` está fora do escopo deste comando; para isso existe higiene assistida.
