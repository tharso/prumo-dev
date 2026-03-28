# Playbook Operacional: Adapter Gemini CLI

Este documento existe para evitar uma preguiça simétrica à do universo Claude: achar que `Gemini CLI` e `Antigravity` são a mesma coisa só porque carregam o mesmo sobrenome.

Não são.

`Gemini CLI` é o host de terminal. É por ele que faz sentido começar a validar o lado Gemini do Prumo sem levar interface gráfica, browser agent e política de autonomia para a dança antes da hora.

## 1. Estado atual deste host

Hoje, a situação do `Gemini CLI` é esta:

1. a base documental oficial é boa;
2. o contrato do runtime já está pronto para ele;
3. a validação de campo neste projeto já foi feita e mostrou desvio grave de comportamento.

Traduzindo: aqui o problema deixou de ser abstrato. O host tentou improvisar o próprio runtime em vez de obedecer ao comando.

## 1.1. Resultado da validação de campo (2026-03-21)

O teste real no `Gemini CLI` mostrou um retrato pior do que o do `Claude Code`:

1. `prumo` foi ignorado;
2. o host leu `PRUMO-CORE.md`, `CLAUDE.md`, `PAUTA.md`, `INBOX.md` e outros arquivos por conta própria;
3. ao pedir `prumo briefing --workspace . --refresh-snapshot`, o host não executou o comando e ainda escreveu `_state/briefing-state.json` na unha;
4. ao pedir `prumo start --workspace . --format json`, o host fabricou um JSON próprio em vez de devolver a saída real do runtime.

Conclusão prática:

1. `Gemini CLI` está reprovado, por enquanto, em invocação curta;
2. `Gemini CLI` está reprovado, por enquanto, em briefing explícito;
3. `Gemini CLI` está reprovado, por enquanto, em consumo do `start --format json`;
4. o risco real aqui é autonomia burra com confiança alta.

## 2. Fontes oficiais que importam

1. Google for Developers summary: [developers.google.com/gemini-code-assist/docs/gemini-cli](https://developers.google.com/gemini-code-assist/docs/gemini-cli)
2. Repositório oficial: [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)

O que isso nos autoriza a assumir:

1. `Gemini CLI` é agente de terminal com shell local;
2. operações de arquivo são parte do terreno oficial;
3. MCP, ferramentas e saídas estruturadas já fazem parte do ecossistema;
4. não precisamos inventar metafísica para justificar um adapter fino.

## 3. O que ele não é

`Gemini CLI` não deve ser tratado como:

1. `Antigravity` sem interface;
2. "o mesmo adapter do Codex, mas com outro logo";
3. host que herda automaticamente tudo o que funcionou em `Codex`.

Se cairmos nisso, trocamos arquitetura por superstição com documentação em PDF.

## 4. Porta canônica

Para `Gemini CLI`, o contrato é este:

1. se o usuário disser `Prumo`, `bom dia, Prumo` ou equivalente, o host deve rodar `prumo`;
2. se o pedido for briefing explícito, o host deve rodar `prumo briefing --workspace . --refresh-snapshot`;
3. se o host quiser renderizar ações com mais inteligência, deve usar `prumo start --format json`.

## 5. Como consumir `prumo start --format json`

O adapter do `Gemini CLI` deve respeitar:

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

Em português curto:

1. `state_flags` e `degradation` vêm antes da prosa; o runtime não está pedindo interpretação literária
2. `selection_contract` manda no aceite curto
3. `kind = shell` -> executar `shell_command`
4. `kind = host-prompt` -> usar `host_prompt`
5. `adapter_hints.preferred_entrypoint` -> porta curta
6. `adapter_hints.briefing_entrypoint` -> briefing explícito
7. `adapter_hints.structured_entrypoint` -> rota estruturada

## 6. Regras práticas

1. Resolver o workspace pelo diretório atual quando possível.
2. Respeitar `AGENT.md`, `AGENTS.md` e `CLAUDE.md` como wrappers do runtime.
3. Não assumir paridade automática com `Codex` só porque ambos vivem bem no terminal.
4. Não contaminar esse adapter com premissas de `Antigravity`.
5. Tratar permissões locais por app. Se um dia formos usar integrações locais de macOS por este host, a autorização será do app/processo dele, não do vizinho.
6. Nunca ler arquivos para "simular" `prumo` se o comando ainda não foi executado.
7. Nunca escrever `_state/briefing-state.json` ou qualquer outro arquivo de estado fingindo ser o runtime.
8. Nunca sintetizar JSON de `start`; ou roda `prumo start --format json`, ou assume que falhou.

## 6.1. Ordem obrigatória de leitura

No `Gemini CLI`, esta ordem não é capricho. É contenção:

1. `degradation`
2. `next_move`
3. `selection_contract`
4. `state_flags`
5. `actions[]`
6. só depois `message`

Se o host começar pelo texto e "entender o espírito", ele volta a improvisar runtime na unha.

## 7. Checklist de aceite

O adapter `Gemini CLI` passa quando:

1. `Prumo` vira `prumo`;
2. briefing explícito vira `prumo briefing --workspace . --refresh-snapshot`;
3. `prumo start --format json` volta com estrutura íntegra e o host a respeita;
4. o host não improvisa briefing fora do runtime;
5. o usuário não precisa decorar subcomando para começar.

Status atual deste checklist:

1. `Prumo` vira `prumo` -> `NAO`
2. briefing explícito vira `prumo briefing --workspace . --refresh-snapshot` -> `NAO`
3. `prumo start --format json` volta com estrutura íntegra e o host a respeita -> `NAO`
4. o host não improvisa briefing fora do runtime -> `NAO`
5. o usuário não precisa decorar subcomando para começar -> `NAO`

## 8. Risco principal

O risco principal aqui já deixou de ser teórico:

1. o host agir como se "entender o espírito do Prumo" fosse licença para não executar `prumo`;
2. o adapter textual do workspace ser lido como literatura motivacional, não como contrato operacional;
3. o projeto subestimar o custo de conter autonomia ruim em host de terminal.

## 9. Próximo passo neste host

1. endurecer os wrappers do workspace contra improviso de briefing e escrita de estado;
2. tratar `Gemini CLI` como host em falha real de adapter, não como host "quase validado";
3. seguir para o próximo host sem deixar esse comportamento sequestrar o roadmap;
4. voltar ao `Gemini CLI` só depois de decidir se vale construir contenção host-específica para esse grau de autonomia ruim.
