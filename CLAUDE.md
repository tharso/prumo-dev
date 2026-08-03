# Prumo

Sistema de organização de vida pessoal com IA. Transforma o Claude (ou qualquer agente) em interface para capturar, processar, lembrar e cobrar. Dados em Markdown local, sem cloud, sem lock-in.

## Stack

- **Runtime:** Python 3.10+ (`runtime/prumo_runtime/`), empacotado via hatchling — mínima ditada pela VM do Cowork; `prumo update` é o único comando que exige 3.11 (tomllib), com gate legível (#301)
- **Skills:** Markdown com referências cruzadas (`skills/`)
- **Scripts operacionais:** Bash e Python (`scripts/`)
- **Testes:** unittest (Python) + jobs de smoke no CI (instalação via scripts Bash/PowerShell e wheel)
- **CI:** GitHub Actions (Ubuntu, macOS, Windows)
- **Distribuição:** marketplace do Cowork via `marketplace.json` + `plugin.json`
- **Repo:** https://github.com/tharso/prumo (público, MIT)

## Estrutura do projeto

```
skills/              ← fonte canônica das skills (portáveis, qualquer agente lê)
  prumo/             ← skill principal (setup/onboarding, core, references, modules —
                       faxina, sanitize e doctor viram módulos aqui na #172)
  briefing/          ← morning briefing
  higiene/           ← revisão assistida do workspace (botão desde a #172)
  acervo/ fim/ menu/ ← navegação do limbo, encerramento, manual
  abrir/ decidir/    ← entrada rápida e superfície de despacho (estruturais)
runtime/             ← runtime Python (CLI local)
  prumo_runtime/     ← código do runtime
  tests/             ← unit tests
scripts/             ← scripts de operação e distribuição
plugin.json          ← manifesto do plugin (aponta pra skills/)
marketplace.json     ← registro no marketplace do Cowork
pyproject.toml       ← empacotamento Python do runtime
```

### Diretórios removidos (não recriar)

Os seguintes diretórios e arquivos foram removidos em abril/2026 durante a consolidação skills-first. Não recriar: `cowork-plugin/`, `bridges/`, `_lixeira/`, `commands/`, `docs/`, adapter playbooks (`*-ADAPTER-PLAYBOOK.md`), ADRs avulsos na raiz.

**Exceção nomeada (31/07):** `docs/agents/` existe e é legítimo — é config de tooling de agente (issue tracker, labels de triagem, ponteiro de domínio), não documentação de produto, que é o que a consolidação removeu. Nada mais entra em `docs/`. Ver DECISIONS.md de 2026-07-31.

## Planning

- Quando pedirem pra planejar: apenas o plano. Sem execução até aprovação explícita.
- Quando receberem um plano aprovado: seguir exatamente. Flagrar problemas reais e esperar.
- Para features não-triviais (3+ passos ou decisões arquiteturais): entrevistar sobre implementação, UX e tradeoffs antes de executar.
- Não construir para cenários imaginários. Simples e correto vence elaborado e especulativo.
- **Regra zero:** nunca sair codando sem um plano que alinhe expectativas antes. Isso vale pra qualquer mudança que toque mais de um arquivo ou mude comportamento observável.

## Regras operacionais

### Workflow de desenvolvimento

- TDD contextual: features em produção seguem TDD (testes antes do código). Protótipos e explorações podem ter testes depois, mas antes de qualquer merge.
- Commitar com mensagens descritivas em português. Prefixos: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`.
- Bumpar versão em `plugin.json`, `pyproject.toml`, `marketplace.json` e `VERSION` simultaneamente. Versão fora de sincronia é bug.
- Ao encerrar uma sessão de trabalho relevante, revisar o `.prumo-contexto.md` da raiz (local, gitignored) e atualizá-lo se a realidade mudou (estado, decisões, próximos passos); só então atualizar o `updated:` (RFC 3339 com offset). Nunca atualizar apenas o timestamp — narrativa velha com data nova é pior que narrativa velha detectável. Esquecer não quebra nada (a defasagem aparece no índice do Prumo), mas manter em dia é o que faz o Prumo responder com contexto atual quando o Tharso perguntar por este projeto.

### Autoria de commits redigidos por agente

Quando um agente de IA (Cowork, Claude Code, Codex, Antigravity) redige o commit, adicionar trailer `Co-authored-by` no fim da mensagem identificando o agente. Tharso continua como autor primário (aprova e dirige), o agente vira co-autor. Padrão GitHub, renderizado com avatar duplo na UI. Exemplo:

```
fix(setup): auto-default em stdin nao-interativo

[corpo da mensagem]

Co-authored-by: Claude (Cowork) <noreply@anthropic.com>
```

Isso vale apenas para commits onde o agente *efetivamente redige* — código, mensagem, decisão. Commits onde o agente apenas executa comando ditado pelo usuário ficam sem trailer (autoria humana clara). Quando em dúvida, marcar — falsa modéstia atrapalha mais que ruído de log.

O e-mail do trailer acompanha o fornecedor do modelo real: `noreply@anthropic.com` pra Claude, `noreply@openai.com` pra Codex — nunca um domínio único pra todos.

### Loop de desenvolvimento (TDD + agentes)

**Arranjo: Preset A — Executor revisado.** Quem abre a sessão é o **host/gerente** (fala com o humano e orquestra) e também implementa; o **delegado** é a sessão independente que revisa. O arranjo é simétrico em tese, mas na prática o host é o Claude e o revisor é o Codex (ver estado das receitas abaixo). Este é o default do projeto — override por task no chat; mudança durável = editar este bloco e registrar no DECISIONS.md (tópico `governance`).

**CLIs verificados neste projeto em 2026-08-03:**

- **Codex (codex-cli 0.144.3) — VERIFICADO por smoke test:** iniciar `codex exec "<brief>"` (session_id sai no transcript), retomar `codex exec resume <session_id> "<feedback>"`, review dedicado `codex exec review --base main`. Nunca reinvocar stateless entre rounds — perde a memória do round anterior.
- **Claude Code headless — receita padrão, NÃO verificada:** `claude -p "<brief>" --output-format json` (session_id no JSON) → `claude -p --resume <session_id> "<feedback>"`. Smoke de 03/08 falhou por OAuth expirado do CLI. Antes de usar Claude como delegado: rodar `claude login` e repetir o smoke.
- **Gemini — presente, fora do arranjo default:** testado como revisor e rebaixado (edita arquivos em plan mode, alucina achados). Se for usado: worktree isolado, e os achados são carregados pelo Codex. Entrada no arranjo só via decisão explícita.

Cada task não-trivial de código segue este loop:

1. **Planejar.** Ler os canônicos (DECISIONS.md via índice temático, gotchas.md, código tocado) antes de propor. Pra feature não-trivial (3+ passos ou decisão arquitetural), a saída é uma **spec curta** na issue: problema, contratos de entrada/saída, regras de domínio, critérios de aceite, fora-de-escopo. A spec é a fonte da verdade da task.
2. **TDD.** Teste antes do código (TDD contextual, como no Workflow acima).
3. **Implementar em branch.** O host implementa. Nunca direto na main. Trailer de co-autoria conforme "Autoria de commits" acima.
4. **Revisão independente (cética por design).** Quem escreveu não aprova. O revisor não vê o chat — só diff, testes e brief autocontido (task, critérios de aceite, arquivos, restrições relevantes deste CLAUDE.md, trechos pertinentes de DECISIONS/gotchas, branch). Round 1 com o comando de review verificado; rounds 2+: corrigir na MESMA branch e retomar a MESMA sessão via resume, descrevendo o que mudou. P1 do revisor: presumir certo até prova em contrário. Esperado 2–5 rounds; mais de 5 sem convergir → escalar pro Tharso descrevendo o impasse.
5. **Push + PR.** Corpo abre com o elenco `[dev: <modelo> session <id> | review: <modelo> session <id> | N rounds, aprovado]` + resumo round-a-round; o mesmo resumo vai em comentário na issue. Transcript bruto não vai pro repo; session_ids ficam pra auditoria e retomada.
6. **Merge — delegação registrada (DECISIONS.md 2026-08-03).** Espelha a governança abaixo, sem mudá-la: issue criada pelo agente dentro dos limites (bug trivial, refactor pequeno, sem mudança de comportamento observável) + revisor aprovado + CI verde → o agente mergeia e fecha sem re-perguntar. Pausa obrigatória com OK explícito do Tharso: feature nova, mudança de UX/comportamento observável, `plugin.json`/`marketplace.json`/`pyproject.toml`/`scripts/baseline.json`, nova dependência, mudança de contrato, ação irreversível. Revogável por uma linha no chat.
7. **Pós-merge.** Atualizar canônicos (DECISIONS.md/gotchas.md) — só o host escreve neles; delegados reportam. Mudança de comportamento valida com smoke manual antes de declarar concluída.

### Issues e documentação

- Issues no GitHub como unidade de trabalho: toda feature, bug ou refactor vira issue antes da implementação.
- O agente cria a issue com critérios de aceite claros e assina como ele mesmo (não em nome do Tharso).
- Toda ação relevante numa issue deve ter comentário explicando o que foi feito e por quê.
- Issues submetidas pelo usuário ficam como "review" após resolução (Tharso fecha). Issues criadas pelo agente podem ser fechadas por ele se passaram nos testes e critérios de aceite.
- **Anti-zombie:** ao postar comentário "implementação concluída" ou equivalente, a próxima ação é fechar a issue. Issue aberta com conclusão declarada é zombie — o workflow `zombie-issue-detector` aplica `status/zombie` após 7 dias.

### Governança agente/humano

- Features novas: criar issue e aguardar aprovação antes de implementar.
- Bugs triviais e refactors pequenos (< 3 arquivos, sem mudança de comportamento): pode executar direto.
- Qualquer mudança que altere a experiência do usuário final do Prumo: precisa de aprovação.
- Qualquer mudança em `plugin.json`, `marketplace.json` ou `pyproject.toml`: precisa de aprovação.
- **Touchpoint sync (prumo.me):** toda mudança que afete usabilidade, comandos, fluxo de instalação ou filosofia do produto deve ser verificada contra a landing page em https://prumo.me. Se a página não reflete a realidade do produto, ajustar antes de considerar a mudança concluída. Repo: `tharso/prumo_landing-page` (Vercel auto-deploy). Local: `/Users/tharsovieira/Documents/DailyLife/Projetos/Prumo_LandingPage`. Ver DECISIONS.md 2026-05-18.

### Quality gate e baseline (`scripts/baseline.json`)

O projeto tem um quality gate que congela as métricas do `scripts/baseline.json` (ruff, cobertura, maior arquivo, rota do briefing). A catraca só anda num sentido — o codebase só pode manter ou melhorar. Exceção regrada: `briefing_f0f1_words` mede um CONTRATO (palavras da rota) e pode SUBIR em dois casos, ambos com aprovação explícita do dono e entrada no `DECISIONS.md` (nunca só a `_note` do baseline): (a) **contrato novo** aprovado (decisão de 27/07); (b) **recalibração de instrumento** aprovada — quando se descobre gasto que já existia mas o termômetro não media (decisão da #248, também de 27/07) — sempre acompanhada de teste anti-regressão que impeça o mesmo ponto cego de voltar.

**Regras para o agente:**

- **Nunca** editar `scripts/baseline.json` sem aprovação explícita do Tharso.
- Quando um PR melhorar uma ou mais métricas (cobertura sobe, violações caem, arquivo encolhe), o agente **deve** sinalizar isso ativamente — "a métrica X melhorou de A para B, posso apertar o baseline?" — e aguardar confirmação antes de commitar a atualização.
- A proposta de atualização deve incluir os valores antigos e novos lado a lado, para que Tharso possa avaliar se faz sentido apertar agora ou deixar margem.
- Atualizar o baseline é uma decisão de governança, não de código. O agente propõe, Tharso decide.
- Quando o baseline for atualizado, registrar no `DECISIONS.md` com data e razão.

### Restrições

- **Nunca** reintroduzir a camada de plugin como intermediária entre skills e consumidor. O Prumo é skills-first.
- **Nunca** criar novos playbooks de adapter. Essa fase acabou.
- **Nunca** commitar direto na main sem CI verde.
- **Nunca** deletar arquivos sem verificar referências.
- **Nunca** mudar configs de produção sem explicação na issue.
- **Nunca** commitar, abrir PR ou criar tag em `tharso/prumo` (repo público). Esse repo é espelho gerado automaticamente a partir de `prumo-dev/main` via workflow `.github/workflows/mirror-to-prumo.yml`. Qualquer coisa empurrada direto lá é sobrescrita no próximo push do dev. Todo desenvolvimento acontece em `tharso/prumo-dev`.

## Edit Safety (código)

- Reler o arquivo antes e depois de editar. O tool de edição falha silenciosamente quando o trecho mudou desde a última leitura.
- Em qualquer rename ou mudança de assinatura: buscar chamadas diretas, referências de tipo, imports, re-exports, mocks de teste. Grep não é AST, assumir que sempre perdeu algo e verificar.
- Verificar que nada referencia um arquivo antes de deletá-lo.
- Refactors em fases: máximo 5 arquivos por rodada, depois verificar e obter aprovação.
- Antes de refatorar arquivo grande (>300 LOC): remover código morto e imports não usados primeiro. Commitar limpeza separadamente.
- Comentários: default é não comentar. Só quando o PORQUÊ não é óbvio.

## Integridade referencial (conteúdo/skills)

- Antes de editar um arquivo que referencia outros (ou é referenciado), verificar que as referências existem e estão corretas.
- Reler antes e depois de editar. Compactação de contexto destrói memória de conteúdo textual.
- Reorganização em fases, por área/tema. Reorganizações grandes quebram referências implícitas.
- Manter tom e formato existentes nos arquivos. Não reescrever conteúdo num estilo diferente sem aprovação.

## Configuração e secrets

- `.env`, credentials, tokens ficam fora do repo. Verificar `.gitignore` antes de qualquer commit.
- Qualquer mudança em arquivo de config deve ter comentário na issue explicando o que mudou e por quê.

## Context Management

- Após 10+ mensagens: reler qualquer arquivo antes de editá-lo. Compactação automática pode ter destruído memória do conteúdo.
- Se notar degradação de contexto: rodar /compact proativamente. Escrever estado da sessão para que forks possam continuar.
- Cada leitura de arquivo é limitada a 2.000 linhas. Para arquivos com mais de 500 linhas: usar offset e limit para ler em chunks.

## Self-Correction

- Após qualquer correção do usuário: registrar o padrão em gotchas.md. Converter erros em regras.
- Se um fix não funcionar após duas tentativas: parar. Ler a seção inteira relevante de cima a baixo. Declarar onde o modelo mental estava errado.

## Communication

- Quando o usuário disser "sim", "faz", "manda": executar. Não repetir o plano.
- Quando apontarem código ou conteúdo existente como referência: estudar e replicar os padrões.
- Trabalhar a partir de dados concretos. Não chutar. Se falta informação, perguntar.
- **Didática nos pontos de decisão.** Toda discussão de decisão (proposta, trade-off, merge, risco) em linguagem não-técnica, como pra um aluno esperto do ensino médio: primeiro a analogia ou a consequência prática, depois o termo técnico entre parênteses — o usuário aprende o vocabulário em vez de depender de tradução. Execução rotineira não vira aula: resumo curto e claro.
- **Decisão só conta como aprovada se foi compreendida.** "Ok" seco e imediato pra algo com consequência, aprovação sem nenhuma pergunta em tema novo ou aprovações em série disparam, antes de executar, uma checagem de entendimento: reformular em uma frase o que muda, a consequência prática e o custo de reverter, e fechar com uma pergunta concreta que só quem entendeu responde. (Isso não revoga o "sim = executar" de rotina — a checagem é só pra decisão pesada em tema novo aprovada rápido demais.)
- **Retomada.** Suspeitou depois que algo passou batido (consequência que só ficou visível agora, jargão que ficou sem explicar, aprovação rápida demais na época)? Retomar o tema no próximo contato e se certificar. "Já foi aprovado" não encerra o assunto: entendimento pendente é dívida.
- **Grill de domínio.** Regra de negócio nova ou ambígua não entra em código (nem em conteúdo) calada: entrevistar o usuário, uma pergunta por vez, até entendimento mútuo; o entendimento vira critério de aceite/teste e, se relevante, entrada no DECISIONS.md. É a revisão invertida: em vez de o humano ler todo o diff, o agente confere o entendimento do humano.

## Comunicação entre agentes (ambiente de desenvolvimento)

Handover é ferramenta de coordenação entre agentes **dentro do desenvolvimento do Prumo**. Não é feature do produto do usuário final (ver issue #68 e DECISIONS.md de 2026-04-20).

Regras:

- **Artefatos de handover vivem em `dev-archive/`** (gitignored). Nada de handover deve aparecer em `skills/`, `runtime/` ou `scripts/`.
- **Lock entre agentes no produto final**: coordenação no workspace do usuário acontece via `.prumo/state/agent-lock.json`. Sem narrativa, sem PENDING_VALIDATION. **Exceção nomeada (#244):** o escopo `Prumo/Referencias/INDICE.md` usa aquisição atômica de filesystem (`.prumo/state/locks/`) porque ID sequencial não admite duplicata e lock cooperativo tem janela — contrato em `multiagent.md`.
- **Validações cruzadas entre Codex/Cowork/Gemini/Claude durante dev**: podem usar os artefatos em `dev-archive/` como registro histórico ou continuar a prática localmente, desde que não vaze nada disso pra dentro das skills ou do runtime.
- Se uma próxima geração do produto precisar de um contrato de handover de volta, vira issue nova e decisão arquitetural explícita. Não é "reverter a remoção".

## Agent skills

### Issue tracker

Issues no GitHub, em `tharso/prumo-dev`. Ver `docs/agents/issue-tracker.md`.

### Triage labels

Os cinco papéis canônicos mapeados para o vocabulário `status/*` que já existia. Ver `docs/agents/triage-labels.md`.

### Domain docs

Single-context; onde as skills dizem "ADR", é o `DECISIONS.md`. Ver `docs/agents/domain.md`.

## Decisões arquiteturais

Ver `DECISIONS.md` para o log completo. O arquivo tem **índice temático** no topo — use ele pra encontrar decisões por tópico, não confiar só em busca por data ou palavra-chave.

### Antes de qualquer operação arquitetural

Considerar "operação arquitetural" qualquer uma destas:

- mudança de schema, contrato ou interface pública,
- nova dependency ou alteração de dependency existente,
- alteração de API surface (runtime ou skills),
- refactor cross-file ou que afete portabilidade,
- renomear, mover ou deletar pastas canônicas (`skills/`, `runtime/`, `Prumo/`, `.prumo/`),
- alterar contratos entre componentes ou layout de diretório do produto,
- qualquer mudança que afete onboarding, fallback chain, ou comportamento observável pelo usuário final.

Checklist obrigatório:

1. Identificar o tópico principal da operação. Conferir o **vocabulário controlado** no `DECISIONS.md`.
2. Consultar o **índice temático** no topo do `DECISIONS.md` filtrando pelo tópico (e pelo menos um sinônimo, se houver risco).
3. Listar decisões ativas no mesmo tópico. Se houver, ler integralmente cada uma — não confiar no título.
4. Se há conflito potencial — mesmo parcial — declarar ao usuário **antes de prosseguir**. **Nunca revogar silenciosamente uma decisão anterior.**
5. Após decisão tomada, registrar nova entrada no `DECISIONS.md` no formato definido lá (incluindo o campo **"Relações com decisões anteriores"**: revoga, estende, mantém ou "nenhuma identificada após consulta ao índice").
6. Atualizar o índice temático no topo do `DECISIONS.md` adicionando a entrada nova nos tópicos correspondentes.

### Operações manuais (mv, rm, renomeação) com efeito arquitetural

Operações estruturais executadas como `mv`/`rm` manual em pastas canônicas seguem o checklist acima. Adicionalmente: **toda op manual com efeito arquitetural deve ter ao menos um commit de registro** (ainda que seja só `chore: mv X to Y`) ou comentário explícito na issue relacionada explicando o que foi feito e quando. Operação arquitetural sem rastro git é fantasma — some do `git log`, some do `git blame`, e o próximo agente reconstitui a história errada.

Aplicado retroativamente: a renomeação `Prumo/skills/` → `Prumo/skills_OLD/` em 22/04 (Fase Operacional da #73) foi feita sem commit no repo. Esse é exatamente o padrão de fantasma que esta regra quer prevenir. Se a operação tivesse passado por `prumo migrate ...` ou tido um `chore` explícito, o conflito com a #65 teria saltado mais cedo.

## Direção atual do projeto

O Prumo passou por três fases: skill → plugin → runtime. Cada transição deixou resíduos. A direção atual é **skills-first**: a alma do produto vive nas skills (portáveis, legíveis por qualquer agente), o runtime é infraestrutura de suporte. A consolidação foi executada em abril/2026: `cowork-plugin/`, adapter playbooks, ADRs avulsos, `bridges/`, `docs/` e `_lixeira/` foram removidos. `skills/` é a fonte canônica única.
