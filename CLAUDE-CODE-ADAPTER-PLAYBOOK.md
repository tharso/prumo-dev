# Playbook Operacional: Adapter Claude Code

Este documento existe para impedir um erro particularmente preguiçoso: tratar `Claude Code` como se fosse só "o mesmo Cowork sem vitrine".

Não é.

Os dois orbitam o universo Claude, mas o adapter do Prumo não é definido pelo sobrenome do modelo. É definido pela superfície real do host.

## 1. Estado atual deste host

Hoje, a situação do `Claude Code` é esta:

1. a base documental oficial é boa;
2. o contrato do runtime já está pronto para ele;
3. a validação de campo neste projeto já provou shell explícito, mas ainda não fechou invocação natural nem Apple Reminders por app.

Traduzindo sem maquiagem: aqui o terreno é melhor documentado do que no `Cowork`, mas ainda menos testado em produção do que no `Codex`.

## 1.1. Resultado da validação de campo (2026-03-21)

O teste real no `Claude Code` mostrou um retrato misto:

1. `Prumo`, sozinho, ainda caiu em fluxo torto (`prumo:setup` / leitura de arquivos) em vez de bater na porta canônica do runtime;
2. comandos explícitos passaram:
   - `prumo --version`
   - `prumo start --workspace . --format json`
   - `prumo briefing --workspace . --refresh-snapshot`
3. `Apple Reminders` continuou bloqueado no host, mesmo depois de reset de TCC e auth repetido;
4. o painel de `Privacidade e Segurança > Lembretes` mostrou apenas `Terminal.app`, não `Claude Code`.

Conclusão prática:

1. `Claude Code` está aprovado como host com shell;
2. `Claude Code` está reprovado, por enquanto, em invocação natural;
3. `Claude Code` está bloqueado, por enquanto, em `Apple Reminders` por limitação operacional do app/TCC.

## 2. Fontes oficiais que importam

1. Overview: [code.claude.com/docs/en/overview](https://code.claude.com/docs/en/overview)
2. CLI reference: [code.claude.com/docs/en/cli-reference](https://code.claude.com/docs/en/cli-reference)
3. Plugins reference: [code.claude.com/docs/en/plugins-reference](https://code.claude.com/docs/en/plugins-reference)
4. Slash commands / skills: [code.claude.com/docs/en/slash-commands](https://code.claude.com/docs/en/slash-commands)

O que isso nos autoriza a assumir:

1. `Claude Code` é superfície first-class de terminal/CLI.
2. Shell local e leitura de arquivos são parte do terreno oficial.
3. Skills, comandos e plugins existem como sistema formal.

## 3. O que ele não é

`Claude Code` não deve ser tratado como:

1. sinônimo de `Cowork`;
2. extensão do marketplace/store do `Cowork`;
3. adapter dependente de slash command legado do plugin.

Se o projeto esquecer isso, reabre exatamente a confusão que levou o Prumo a misturar host, plugin e produto como se fossem sopa.

## 4. Porta canônica

Para `Claude Code`, o contrato é este:

1. se o usuário disser `Prumo`, `bom dia, Prumo` ou equivalente, o host deve rodar `prumo`;
2. se o pedido for briefing explícito, o host deve rodar `prumo briefing --workspace . --refresh-snapshot`;
3. se o host quiser renderizar ações com mais inteligência, deve usar `prumo start --format json`.

## 5. Como consumir `prumo start --format json`

O adapter do `Claude Code` deve respeitar:

1. `adapter_contract_version`
2. `workspace_resolution`
3. `adapter_hints`
4. `state_flags`
5. `degradation`
6. `next_move`
7. `selection_contract`
8. `actions[].kind`
9. `actions[].shell_command`
10. `actions[].host_prompt`

Em português simples:

1. `state_flags` serve para decisão rápida; `google_status` e `apple_reminders_status` servem para detalhe
2. `degradation` existe para evitar pânico burro ou otimismo igualmente burro
3. `selection_contract` manda no aceite curto; não reabra menu depois de aceitação explícita
4. `kind = shell` -> executar `shell_command`
5. `kind = host-prompt` -> usar `host_prompt` como continuação conversacional
6. `adapter_hints.preferred_entrypoint` -> porta curta
7. `adapter_hints.briefing_entrypoint` -> briefing explícito
8. `adapter_hints.structured_entrypoint` -> rota estruturada

## 5.1. Ordem mínima de leitura

Ao consumir JSON:

1. olhar `degradation`;
2. olhar `next_move` e `selection_contract`;
3. olhar `actions[]`;
4. só então usar `message` para acabamento conversacional.

## 6. Regras práticas

1. Resolver o workspace pelo diretório atual quando possível.
2. Respeitar `AGENT.md`, `AGENTS.md` e `CLAUDE.md` como wrappers do runtime.
3. Não cair no reflexo "já que é Claude, vou usar o fluxo do Cowork". Isso seria preguiça com gravata.
4. Não depender de plugin store, registry local ou slash command do `Cowork`.
5. Tratar permissões locais por app. `Claude Code` precisa das próprias permissões para Apple Reminders se quiser usar essa integração.

## 7. Checklist de aceite

O adapter `Claude Code` passa quando:

1. `Prumo` vira `prumo`;
2. briefing explícito vira `prumo briefing --workspace . --refresh-snapshot`;
3. `prumo start --format json` volta com estrutura íntegra e o host a respeita;
4. o host não puxa o plugin do `Cowork` como muleta conceitual;
5. o usuário não precisa decorar subcomando para começar.

Status atual deste checklist:

1. `Prumo` vira `prumo` -> `NAO`
2. briefing explícito vira `prumo briefing --workspace . --refresh-snapshot` -> `SIM`
3. `prumo start --format json` volta com estrutura íntegra e o host a respeita -> `SIM`
4. o host não puxa o plugin do `Cowork` como muleta conceitual -> `SIM` no teste explícito, `NAO` no teste natural
5. o usuário não precisa decorar subcomando para começar -> `NAO`

## 8. Diferença operacional para Cowork

Esta é a parte que precisa ficar tatuada no plano:

1. `Cowork` pode até continuar usando slash command, plugin store e bridge de compatibilidade;
2. `Claude Code` não precisa herdar esse teatro;
3. o adapter de `Claude Code` deve ser avaliado mais perto da lógica do `Codex` do que da do `Cowork`, mas sem copiar contrato no escuro.

## 9. Próximo passo neste host

1. manter registrado que `shell explícito` já passou;
2. tratar `invocação curta` como pendência real do adapter;
3. tratar `Apple Reminders` como bloqueio operacional do host/TCC, não como bug central do Prumo;
4. não deixar essa limitação sequestrar a sequência do roadmap.
