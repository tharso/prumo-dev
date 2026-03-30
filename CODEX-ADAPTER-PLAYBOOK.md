# Playbook Operacional: Adapter Codex

Este documento existe para uma coisa bem específica: impedir que `Codex` vire um adapter "quase óbvio" que cada pessoa implementa na própria cabeça.

`Codex` foi o primeiro host a mostrar, em teste real, comportamento próximo da UX desejada. Isso não o transforma em host preferido do produto. Só o transforma na primeira pista asfaltada.

## 1. O que o host já provou em campo

No laboratório `aVida`, o teste real foi este:

1. abrir uma conversa limpa no Codex;
2. dizer apenas `Prumo`;
3. observar se o host rodava o runtime ou improvisava um briefing professoral por conta própria.

O resultado passou:

1. o Codex detectou o workspace certo;
2. bateu em `prumo`;
3. devolveu o estado do runtime e as próximas ações;
4. não tentou reinventar onboarding.

Em português simples: o Codex já mostrou que consegue agir como campainha, não como dramaturgo.

## 2. Fontes oficiais que importam

1. OpenAI Codex docs: [developers.openai.com/codex/cloud](https://developers.openai.com/codex/cloud)
2. Local shell tool: [developers.openai.com/api/docs/guides/tools-local-shell](https://developers.openai.com/api/docs/guides/tools-local-shell)
3. Repositório oficial: [github.com/openai/codex](https://github.com/openai/codex)

O que isso nos autoriza a assumir sem devaneio:

1. `Codex` é host local de código com shell e arquivos.
2. `AGENTS.md` é superfície legítima de instrução.
3. Não há desculpa elegante para o host fingir que `prumo` não existe quando o workspace está pronto.

## 3. Porta canônica

Para `Codex`, o contrato é este:

1. se o usuário disser `Prumo`, `bom dia, Prumo` ou equivalente, o host deve rodar `prumo`;
2. se o pedido for briefing explícito, o host deve rodar `prumo briefing --workspace . --refresh-snapshot`;
3. se o host quiser renderizar ações com mais inteligência, deve usar `prumo start --format json`.

## 4. Como consumir `prumo start --format json`

O adapter do Codex deve respeitar:

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

Traduzindo sem perfume:

1. `state_flags` decide fluxo rápido; `google_status` e `integration_status` contam o detalhe operacional
2. `degradation.status != ok` significa "preserve o que ainda funciona e trate a avaria sem teatro"
3. `selection_contract` governa aceite curto; não abra menu novo depois de `1`, `a`, `aceitar`, `seguir` ou equivalente
4. `kind = shell` -> executar `shell_command`
5. `kind = host-prompt` -> usar `host_prompt` como continuação conversacional
6. se `next_move.id = kickoff`, não abra menu de confirmação; faça uma segue curta e convide ao despejo inicial
6. `adapter_hints.preferred_entrypoint` -> porta curta
7. `adapter_hints.briefing_entrypoint` -> briefing explícito
8. `adapter_hints.structured_entrypoint` -> rota estruturada

Se o adapter ignorar isso e decidir “interpretar o espírito do JSON”, ele volta a fazer o erro clássico: transformar contrato em horóscopo.

## 4.1. Regra de bolso para a ordem de leitura

Quando a saída vier em JSON:

1. leia `degradation` e veja se há alerta operacional;
2. leia `next_move` e `selection_contract`;
3. só depois use `message` para lapidar a resposta humana.

Se começar pelo textão, o host vira leitor de bula tentando pilotar avião.

## 5. Regras práticas

1. Resolver o workspace pelo diretório atual quando possível.
2. Respeitar `AGENT.md`, `AGENTS.md` e `CLAUDE.md` como wrappers do runtime, não como desculpa para inventar outro produto.
3. Não chamar `briefing` por reflexo quando o runtime já ofereceu alternativa melhor.
4. Não sugerir `setup`, `migrate`, `repair` ou `auth` por conta própria se o runtime já devolveu ação explícita.
5. Tratar integrações opcionais e permissões locais como detalhe do host, não como critério do MVP.
6. Se `Codex` tiver conector oficial para Gmail, Google Calendar ou Google Drive, use isso como fonte primária de contexto externo antes de inventar coleta paralela no runtime.
7. Se trouxer contexto externo, normalize minimamente antes de jogar isso no briefing. Não faça o Prumo mastigar payload cru de conector.

## 6. Checklist de aceite

Um teste de campo do adapter `Codex` passa quando:

1. `Prumo` vira `prumo`;
2. briefing explícito vira `prumo briefing --workspace . --refresh-snapshot`;
3. `prumo start --format json` volta com estrutura íntegra e o host não a distorce;
4. o usuário não precisa decorar subcomando para começar a conversa.

## 7. O que não fazer

1. Não tratar `Codex` como benchmark universal para todos os hosts.
2. Não assumir que sucesso no Codex se transfere automaticamente para `Claude Code`, `Cowork`, `Gemini CLI` ou `Antigravity`.
3. Não transformar este playbook em desculpa para preferir o host. Ele só descreve o primeiro slice implementado.

## 8. Próximo passo depois do Codex

1. `Claude Code` como próximo host da fila, ainda na família Claude mas sem confundir isso com `Cowork`.
2. `Cowork` depois, no papel de adapter fino, não de motor plugin-first.
3. `Gemini CLI` e `Antigravity` como superfícies distintas do universo Gemini.
