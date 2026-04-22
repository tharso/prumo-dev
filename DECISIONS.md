# Decisoes do projeto

Log de decisoes arquiteturais e de processo. Cada entrada registra o contexto, a decisao e as alternativas consideradas. Consultar antes de tomar decisoes que possam contradizer algo ja registrado.

---

## 2026-04-21 — Despacho por intencao substitui bootstrap just-in-case (issue #69)

**Contexto:** O bootstrap do Prumo lia na abertura `AGENT.md`, `PRUMO-CORE.md` inteiro, `PERFIL.md`, `EMAIL-CURADORIA.md`, `briefing-procedure.md`, `PAUTA.md` e `REGISTRO.md` presumindo que a tarefa e briefing matinal. Tres problemas: (1) Prumo virou ferramenta quase exclusiva de briefing, subutilizado para projetos, artigos, brainstorms e analises; (2) cada sessao nascia com ~10-15K tokens gastos em leitura especulativa; (3) abertura passiva ("bom dia, como posso ajudar?") sem se invocar como Prumo.

**Decisao:** Substituir bootstrap just-in-case por despacho por intencao (just-in-time). Abertura carrega so o minimo (AGENT.md + PRUMO-CORE Parte 1) e faz scan leve de PAUTA (cabecalhos) e REGISTRO (ultimas 5-10 linhas). Agente cumprimenta proativamente com 2-4 opcoes concretas ancoradas no scan + fuga explicita (`outra coisa`). Modulos operacionais (briefing, curar email, analise, etc.) sao carregados sob demanda conforme a intencao do usuario. Dispatch hibrido: tabela de gatilhos + pergunta de refinamento em caso de zero match ou dois matches. Zero adivinhacao silenciosa. "Bom dia" sozinho nao dispara briefing.

**Alternativas consideradas:**
- Manter bootstrap e so enxugar leitura inicial -> rejeitado, o problema nao e tamanho da leitura, e a presuncao de intencao. Briefing como default bloqueia os outros usos.
- Dispatch puramente por tabela de palavras-chave -> rejeitado, fragil com linguagem natural. Ambiguidade resolvida com pergunta curta vence heuristica sofisticada.
- Abertura minimalista sem scan ("bom dia. sobre o que vamos trabalhar?") -> rejeitado, regressao de interface. Parceiro de trabalho real usa o contexto que tem para sugerir, nao fica esperando comando. Scan leve (nao briefing) ancora as opcoes na realidade.

---

## 2026-04-21 — tharso-voice nao distribuido com produto publico

**Contexto:** Durante o design do modulo de dispatch (issue #69), a intencao "escrever artigo" naturalmente precisa ativar alguma skill de voz editorial. No workspace do Tharso existe `tharso-voice` (skill pessoal que captura o estilo editorial dele). Risco: referenciar `tharso-voice` dentro do produto publico do Prumo significaria que todo usuario que instalar o plugin receberia uma skill especifica do Tharso, seja via bundle, seja via dependencia declarada em `plugin.json`/`marketplace.json`.

**Decisao:** Skills pessoais ficam categoricamente separadas do produto publico. No modulo de dispatch, a intencao "escrever artigo" referencia a capacidade genericamente ("se existir skill pessoal de voz no workspace, ativa-la"), nunca nomeando `tharso-voice` ou qualquer outra skill pessoal especifica. Nenhuma skill pessoal entra em `skills/`, `plugin.json`, `marketplace.json` ou como dependencia declarada. Cada usuario traz sua propria skill de voz (ou nenhuma) para o workspace dele.

**Alternativas consideradas:**
- Incluir `tharso-voice` como skill opcional do bundle com flag de ativacao -> rejeitado, opcional instalado por padrao ainda e distribuicao. Resolve nada.
- Renomear `tharso-voice` para algo generico ("personal-voice") e distribuir vazia -> rejeitado, skill vazia nao tem utilidade e confunde usuarios. Cada pessoa precisa construir a propria.
- Documentar em README que usuarios podem adicionar skill de voz propria -> aceito como complemento, nao como substituto da regra. O produto tem que funcionar sem skill de voz instalada.

---

## 2026-04-20 — HANDOVER sai do produto do usuario (issue #68)

**Contexto:** `HANDOVER.md` nasceu como ferramenta de coordenacao entre agentes no desenvolvimento do proprio Prumo (Codex, Cowork, Gemini validando codigo um do outro). A pratica vazou pro produto final: cada workspace de usuario carregava um artefato narrativo pesado, com status `PENDING_VALIDATION`/`APPROVED`/`REJECTED`/`CLOSED`, logica de validacao cruzada, comando `/prumo:handover`, regras de briefing que chamavam handover e politicas de leitura que carregavam o arquivo todo. Usuario final nao orquestra dois agentes validando codigo um do outro. O artefato era peso morto no briefing e no contexto.

**Decisao:** Remover HANDOVER.md e `/prumo:handover` do produto do usuario. Coordenacao entre agentes no produto final passa a acontecer exclusivamente via `.prumo/state/agent-lock.json` (lock curto, sem narrativa). Handover como pratica de dev continua existindo, mas restrita a `dev-archive/` (gitignored) no repositorio de desenvolvimento. Triade de limpeza ficou clara: `sanitize` cuida de sistema (`.prumo/`, automatico com cooldown), `faxina` cuida de arquivos do usuario (`Prumo/`, automatica no briefing), `higiene` cuida de manutencao assistida do workspace do usuario (pergunta antes de mexer).

**Alternativas consideradas:**
- Manter HANDOVER como feature avancada opcional → rejeitado, peso morto na leitura de briefing e violacao do principio de que o produto e agnostico de multiagente no nivel de produto final.
- Matar sanitize junto com HANDOVER (achavam que `sanitize` era so sobre compactar handover) → rejeitado, verificacao do codigo mostrou que sanitize cuida de todo o territorio tecnico do sistema (`.prumo/backups/`, `.prumo/cache/`, `.prumo/state/`). Descobriu-se sobreposicao com faxina; solucao foi refocalizar sanitize em `.prumo/` e faxina em `Prumo/`.
- Deletar todo o historico de validacoes cruzadas de marco/2026 → rejeitado, 122KB com 30 validacoes reais entre agentes sao valor historico do desenvolvimento. Preservados em `DEV_Prumo/dev-archive/HANDOVER-2026-03.md` fora do produto e fora do repo publico.

---

## 2026-04-15 — Nova estrutura de workspace com fallback skills-first (issue #65)

**Contexto:** Quando o runtime CLI nao esta disponivel (Cowork sandbox, maquina sem instalacao), o agente trava porque o AGENT.md proibe ler arquivos para "simular" e nao oferece fallback. As skills nao sao copiadas para o workspace durante a instalacao, entao mesmo a rota de fallback nao tem material para operar.

**Decisao:** Adotar a estrutura PrumoPilot como padrao: raiz e territorio do usuario, `Prumo/` contem dados operacionais + copia das skills, `.prumo/` contem infraestrutura do sistema (state, logs, PRUMO-CORE.md). AGENT.md ganha cadeia de fallback: slash command -> runtime CLI -> skill direto. A regra "nao leia arquivo para simular" e substituida pela cadeia de fallback (skill direto e operacao legitima, nao simulacao).

**Alternativas consideradas:**
- Symlink de skills para o repo de dev -> rejeitado, acopla workspace de usuario ao repo de desenvolvimento. Mudancas no repo quebram o workspace instantaneamente.
- Manter tudo na raiz (estrutura DailyLife atual) -> rejeitado, mistura arquivos do sistema com arquivos do usuario e nao escala.
- Depender exclusivamente do plugin para carregar skills -> rejeitado, amarra a uma plataforma (Cowork) e contradiz skills-first.

---

## 2026-04-14 — Skills-first: descontinuar cowork-plugin/ e consolidar skills/ como fonte canonica

**Contexto:** O Prumo evoluiu de skill para plugin para runtime. Cada transicao criou uma copia das skills (`cowork-plugin/skills/`) que foi divergindo da fonte original (`skills/`). O resultado: duas copias quase identicas com versoes diferentes (4.17.0 vs 4.16.6), confusao sobre qual editar, e agentes sem saber qual e a fonte canonica.

**Decisao:** `skills/` e a fonte canonica unica. `cowork-plugin/` sera removido apos migracao dos smoke tests e atualizacao do CI. O `plugin.json` na raiz ja aponta para `skills/`, entao o marketplace continua funcionando.

**Alternativas consideradas:**
- Manter as duas pastas com script de sync automatico → rejeitado, complexidade sem beneficio.
- Mover tudo pra `cowork-plugin/` → rejeitado, o nome amarra ao Cowork e contradiz a direcao skills-first.

---

## 2026-04-14 — Remocao do mecanismo de Google Drive snapshots

**Contexto:** O briefing usava Google Docs como cache intermediario para emails e calendario (via Apps Script rodando a cada 15 min no Drive de cada conta). O mecanismo nunca foi configurado pelo usuario e o briefing perdia ~45s tentando ler snapshots inexistentes antes de cair no fallback (Gmail/Calendar MCP direto).

**Decisao:** Remover toda a camada de snapshots. Gmail MCP e Calendar MCP sao a fonte primaria. Arquivos de Apps Script, referencias no core, e o ASSERT que priorizava snapshots foram removidos.

**Alternativas consideradas:**
- Manter como fallback opcional → rejeitado, codigo morto que confunde agentes e desperdiça tempo de briefing.
- Configurar os Apps Scripts de verdade → rejeitado, o MCP direto funciona e e mais simples.

---

## 2026-04-14 — Criacao do CLAUDE.md como contrato operacional

**Contexto:** O projeto tinha 4 ADRs, playbooks de adapter, e documentos de jurisdicao, mas nenhum arquivo que dissesse a um agente "como se comportar aqui dentro" de forma unificada. Cada agente precisava descobrir as regras por conta propria.

**Decisao:** Criar CLAUDE.md na raiz como contrato operacional unico. AGENT.md e AGENTS.md sao ponteiros. Decisoes vao no DECISIONS.md.

**Alternativas consideradas:**
- Usar apenas ADRs → rejeitado, ADRs documentam decisoes pontuais mas nao dao instrucoes operacionais.
- Colocar regras no README → rejeitado, README e pra humanos entenderem o projeto, nao pra agentes operarem.
