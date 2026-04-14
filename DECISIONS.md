# Decisoes do projeto

Log de decisoes arquiteturais e de processo. Cada entrada registra o contexto, a decisao e as alternativas consideradas. Consultar antes de tomar decisoes que possam contradizer algo ja registrado.

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
